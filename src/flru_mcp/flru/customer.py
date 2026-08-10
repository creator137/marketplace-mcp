from __future__ import annotations

from bs4 import BeautifulSoup

from flru_mcp.flru.client import FlruClient
from flru_mcp.flru.models import Customer
from flru_mcp.flru.parsers import clean_text


class CustomerService:
    def __init__(self, client: FlruClient):
        self.client = client

    async def get_customer(self, profile_url: str) -> dict:
        html = await self.client.get_text(profile_url)
        soup = BeautifulSoup(html, "lxml")
        name = clean_text((soup.select_one("h1") or soup.select_one("[itemprop='name']")).get_text(" ", strip=True) if (soup.select_one("h1") or soup.select_one("[itemprop='name']")) else None)
        text = soup.get_text(" ", strip=True)
        customer = Customer(name=name, profile_url=profile_url)
        if "Зарегистрирован" in text:
            customer.registration_date = clean_text(text.split("Зарегистрирован", 1)[1][:80])
        return customer.model_dump() | {"reviews": []}

