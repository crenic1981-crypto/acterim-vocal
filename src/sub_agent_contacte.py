"""Sub-agent Contacte — identificare contacte decizionale. Portabilul dirigentului = prioritate absolută."""
from __future__ import annotations
import asyncio, re
import httpx
from bs4 import BeautifulSoup

RE_MOBILE_FR = re.compile(r"(?:\+33\s?|0)\s?[67](?:[\s.\-]?\d{2}){4}")
RE_EMAIL = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
GENERIC_PREFIXES = ("contact@", "info@", "accueil@", "secretariat@")


def _normalize_phone(p: str) -> str:
    digits = re.sub(r"\D", "", p)
    if digits.startswith("33"):
        digits = "0" + digits[2:]
    if len(digits) != 10:
        return ""
    return f"{digits[0:2]} {digits[2:4]} {digits[4:6]} {digits[6:8]} {digits[8:10]}"


def _is_mobile(p: str) -> bool:
    d = re.sub(r"\D", "", p)
    return len(d) == 10 and d[1] in ("6", "7")


async def _fetch(url: str, client: httpx.AsyncClient) -> str:
    try:
        r = await client.get(url, timeout=15, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 ACTERIM-Bot"})
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return ""


def _extract_from_text(text: str) -> tuple[set[str], set[str]]:
    phones = {_normalize_phone(m.group()) for m in RE_MOBILE_FR.finditer(text)}
    phones.discard("")
    phones = {p for p in phones if _is_mobile(p)}
    emails = set(RE_EMAIL.findall(text))
    return phones, emails


async def _from_site(site: str, client: httpx.AsyncClient) -> tuple[set[str], set[str]]:
    if not site:
        return set(), set()
    if not site.startswith("http"):
        site = "https://" + site
    html = await _fetch(site, client)
    if not html:
        return set(), set()
    soup = BeautifulSoup(html, "lxml")
    # Cautam si pe pagina contact
    pages = {site}
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if "contact" in href or "mentions" in href or "equipe" in href:
            full = href if href.startswith("http") else site.rstrip("/") + "/" + href.lstrip("/")
            pages.add(full)
        if len(pages) >= 4:
            break
    phones, emails = set(), set()
    for p in pages:
        h = await _fetch(p, client)
        ph, em = _extract_from_text(h)
        phones |= ph
        emails |= em
    return phones, emails


async def run(siren: str, dirigeant: str = "", site: str = "", societe: str = "") -> dict:
    async with httpx.AsyncClient() as client:
        phones, emails = await _from_site(site, client)

    contacts: list[dict] = []
    # Contact 1 = dirigeant
    c1: dict = {"nom": dirigeant or "Dirigeant inconnu", "fonction": "Gérant", "prio": 1}
    # Heuristică email dirigeant: prefer nu generic
    pro_emails = [e for e in emails if not any(e.lower().startswith(p) for p in GENERIC_PREFIXES)]
    if pro_emails:
        c1["email"] = pro_emails[0]
    if phones:
        c1["tel"] = sorted(phones)[0]
        c1["wa"] = True  # presupunere — mobil FR
    if not c1.get("tel") and not c1.get("email"):
        c1["coordonnees_manquantes"] = True
    contacts.append(c1)

    # Contact generic email firmă
    generic = [e for e in emails if any(e.lower().startswith(p) for p in GENERIC_PREFIXES)]
    if generic:
        contacts.append({
            "nom": "Secrétariat",
            "fonction": "Secrétariat",
            "email": generic[0],
            "prio": 3,
        })

    flags = []
    if not phones and not emails:
        flags.append("contacts_incomplets")

    return {
        "siren": siren,
        "societe": societe,
        "contacts": contacts,
        "nb_contacts": len(contacts),
        "flags": flags,
    }


async def run_batch(items: list[dict]) -> list[dict]:
    sem = asyncio.Semaphore(5)
    async def _one(it):
        async with sem:
            return await run(**it)
    return await asyncio.gather(*[_one(i) for i in items])
