from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

PRODUCTS = [
	{"id": "rice", "name": "Rice", "shelf_life_days": 180},
	{"id": "wheat", "name": "Wheat", "shelf_life_days": 150},
	{"id": "sugar", "name": "Sugar", "shelf_life_days": 365},
]

STORES = [f"store_{i}" for i in range(1, 6)]

class DataStore:
	def __init__(self) -> None:
		self.now = datetime.utcnow()
		self.inventory: Dict[Tuple[str, str], Dict[str, float]] = {}
		self.transactions: pd.DataFrame = pd.DataFrame()
		self.offers: pd.DataFrame = pd.DataFrame()
		self.delivery_bookings: Dict[str, Dict] = {}
		self.logistics_tracking: Dict[str, Dict] = {}
		self.local_prices: Dict[str, float] = {}
		self.online_prices: Dict[str, float] = {}
		self._generate_all()

	def _generate_all(self) -> None:
		self._generate_inventory()
		self._generate_transactions()
		self._generate_offers()
		self._generate_prices()

	def reset(self) -> None:
		self.__init__()

	def _generate_inventory(self) -> None:
		for store in STORES:
			for product in PRODUCTS:
				key = (store, product["id"])
				qty = random.randint(200, 800)
				expiry_date = self.now + timedelta(days=product["shelf_life_days"]) \
					- timedelta(days=random.randint(0, product["shelf_life_days"] // 2))
				self.inventory[key] = {
					"quantity": float(qty),
					"expiry_date": expiry_date,
				}

	def _generate_transactions(self) -> None:
		records: List[Dict] = []
		start = self.now - timedelta(days=120)
		for day in range(120):
			date = start + timedelta(days=day)
			for store in STORES:
				for product in PRODUCTS:
					base = 20 if product["id"] == "rice" else 15 if product["id"] == "wheat" else 10
					seasonality = 1.0 + 0.2 * np.sin(day / 14.0)
					trend = 1.0 + day / 400.0
					demand = np.random.poisson(lam=max(1.0, base * seasonality * trend))
					records.append({
						"date": date.date(),
						"store_id": store,
						"product_id": product["id"],
						"quantity": int(demand),
					})
		self.transactions = pd.DataFrame.from_records(records)

	def _generate_offers(self) -> None:
		records: List[Dict] = []
		for product in PRODUCTS:
			for _ in range(8):
				discount = random.choice([5, 10, 15, 20])
				records.append({
					"product_id": product["id"],
					"description": f"{discount}% off on {product['name']}",
					"discount_percent": discount,
				})
		self.offers = pd.DataFrame.from_records(records)

	def _generate_prices(self) -> None:
		for product in PRODUCTS:
			base = 60 if product["id"] == "rice" else 50 if product["id"] == "wheat" else 40
			self.local_prices[product["id"]] = round(base + random.uniform(-5, 5), 2)
			self.online_prices[product["id"]] = round(base + random.uniform(-6, 6), 2)

	def update_inventory(self, store_id: str, product_id: str, delta: int) -> Dict[str, float]:
		key = (store_id, product_id)
		if key not in self.inventory:
			self.inventory[key] = {"quantity": 0.0, "expiry_date": self.now + timedelta(days=180)}
		self.inventory[key]["quantity"] = float(max(0.0, self.inventory[key]["quantity"] + delta))
		return self.inventory[key]


data_store = DataStore()
