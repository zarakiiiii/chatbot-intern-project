from datetime import datetime, timedelta
from io import BytesIO
from typing import List

import numpy as np
import pandas as pd
from fastapi import APIRouter, Response
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sklearn.linear_model import LinearRegression

from .data import data_store, STORES, PRODUCTS
from .models import (
	InventoryUpdateRequest,
	DeliveryBookingRequest,
	CreditScoreRequest,
	RouteOptimizationRequest,
	ForecastRequest,
	PricingCompareResponse,
)

try:
	from ortools.constraint_solver import routing_enums_pb2
	from ortools.constraint_solver import pywrapcp
	_HAS_ORTOOLS = True
except Exception:
	_HAS_ORTOOLS = False

router = APIRouter()

@router.post("/inventory/update")
def inventory_update(req: InventoryUpdateRequest):
	return data_store.update_inventory(req.store_id, req.product_id, req.quantity_delta)

@router.get("/inventory/get")
def inventory_get(store_id: str, product_id: str):
	key = (store_id, product_id)
	return data_store.inventory.get(key, {"quantity": 0.0, "expiry_date": None})

@router.post("/delivery/book")
def delivery_book(req: DeliveryBookingRequest):
	data_store.delivery_bookings[req.order_id] = {
		"order_id": req.order_id,
		"store_id": req.store_id,
		"address": req.address,
		"items": req.items,
		"status": "booked",
	}
	# create mock tracking
	data_store.logistics_tracking[req.order_id] = {
		"order_id": req.order_id,
		"events": [
			{"ts": datetime.utcnow().isoformat(), "status": "created"},
		]
	}
	return {"message": "delivery booked", "order_id": req.order_id}

@router.get("/logistics/track")
def logistics_track(order_id: str):
	return data_store.logistics_tracking.get(order_id, {"order_id": order_id, "events": []})

@router.post("/credit/score")
def credit_score(req: CreditScoreRequest):
	seed = sum(ord(c) for c in req.retailer_id) % 100
	score = 600 + (seed % 200)
	limit = 50000 + (seed * 100)
	return {"retailer_id": req.retailer_id, "score": score, "limit": limit}

@router.get("/offers")
def get_offers():
	return data_store.offers.to_dict(orient="records")

@router.get("/transactions")
def get_transactions(store_id: str = None, product_id: str = None):
	df = data_store.transactions.copy()
	if store_id:
		df = df[df["store_id"] == store_id]
	if product_id:
		df = df[df["product_id"] == product_id]
	return df.to_dict(orient="records")

@router.get("/pricing/compare", response_model=List[PricingCompareResponse])
def pricing_compare():
	resp: List[PricingCompareResponse] = []
	for p in PRODUCTS:
		pid = p["id"]
		lp = data_store.local_prices[pid]
		op = data_store.online_prices[pid]
		resp.append(PricingCompareResponse(product_id=pid, local_price=lp, online_price=op, delta=lp - op))
	return resp

@router.post("/forecast")
def forecast(req: ForecastRequest):
	results = []
	df = data_store.transactions
	for store in req.stores:
		for product in req.products:
			series = df[(df.store_id == store) & (df.product_id == product)].sort_values("date")
			series = series.reset_index(drop=True)
			if series.empty:
				continue
			series["t"] = np.arange(len(series))
			X = series[["t"]].values
			y = series["quantity"].values
			model = LinearRegression().fit(X, y)
			next_ts = np.arange(len(series), len(series) + req.horizon_days).reshape(-1, 1)
			pred = model.predict(next_ts)
			pred = np.maximum(0, np.round(pred, 0))
			base_date = pd.Timestamp(series["date"].iloc[-1])
			for i, qty in enumerate(pred):
				future_date = (base_date + pd.Timedelta(days=i + 1)).date().isoformat()
				results.append({
					"store_id": store,
					"product_id": product,
					"date": future_date,
					"forecast_quantity": int(qty),
				})
	return {"forecasts": results}

@router.get("/inventory/expiry_reorder")
def expiry_reorder(days_threshold: int = 30, service_level_days: int = 7):
	insights = []
	for (store, product), rec in data_store.inventory.items():
		expiry_date = rec["expiry_date"]
		days_to_expiry = (expiry_date - datetime.utcnow()).days if isinstance(expiry_date, datetime) else 9999
		avg_daily_sales = data_store.transactions[(data_store.transactions.store_id == store) & (data_store.transactions.product_id == product)]["quantity"].tail(30).mean()
		avg_daily_sales = float(0 if np.isnan(avg_daily_sales) else avg_daily_sales)
		reorder_point = int(max(0, avg_daily_sales * service_level_days))
		insights.append({
			"store_id": store,
			"product_id": product,
			"quantity": rec["quantity"],
			"days_to_expiry": days_to_expiry,
			"reorder_point": reorder_point,
			"expiry_risk": days_to_expiry <= days_threshold,
		})
	return {"insights": insights}


def _haversine_km(lat1, lon1, lat2, lon2):
	R = 6371.0
	dlat = np.radians(lat2 - lat1)
	dlon = np.radians(lon2 - lon1)
	alat1 = np.radians(lat1)
	alat2 = np.radians(lat2)
	a = np.sin(dlat/2)**2 + np.cos(alat1) * np.cos(alat2) * np.sin(dlon/2)**2
	c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
	return R * c

@router.post("/routing/optimize")
def optimize_routes(req: RouteOptimizationRequest):
	points = [(req.depot_lat, req.depot_lng)] + [(s.lat, s.lng) for s in req.stops]
	n = len(points)
	if _HAS_ORTOOLS and n > 1:
		# OR-Tools path if available
		dist = np.zeros((n, n), dtype=int)
		for i in range(n):
			for j in range(n):
				if i == j:
					dist[i, j] = 0
				else:
					d = _haversine_km(points[i][0], points[i][1], points[j][0], points[j][1])
					dist[i, j] = int(d * 1000)

			routing = pywrapcp.RoutingModel(n, req.vehicle_count, 0)
			search_params = pywrapcp.RoutingModel.DefaultSearchParameters()
			search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

			def distance_callback(from_index, to_index):
				return int(dist[from_index][to_index])

			routing.SetArcCostEvaluatorOfAllVehicles(distance_callback)
			solution = routing.SolveWithParameters(search_params)
			if not solution:
				return {"routes": []}

			routes = []
			for v in range(req.vehicle_count):
				idx = routing.Start(v)
				path = []
				while not routing.IsEnd(idx):
					next_idx = solution.Value(routing.NextVar(idx))
					path.append(int(idx))
					idx = next_idx
				path.append(int(idx))
				routes.append(path)
			return {"routes": routes, "engine": "ortools"}

	# Heuristic fallback: round-robin assignment with nearest-neighbor per vehicle
	k = max(1, req.vehicle_count)
	vehicle_stops = [[] for _ in range(k)]
	for idx, stop in enumerate(req.stops):
		vehicle_stops[idx % k].append((stop.lat, stop.lng))

	routes = []
	for v in range(k):
		unvisited = vehicle_stops[v][:]
		current = (req.depot_lat, req.depot_lng)
		order = [0]
		while unvisited:
			dists = [(_haversine_km(current[0], current[1], s[0], s[1]), i) for i, s in enumerate(unvisited)]
			_, ni = min(dists, key=lambda x: x[0])
			next_point = unvisited.pop(ni)
			# Map back to index in points (1-based for stops list)
			stop_index = points.index(next_point)
			order.append(stop_index)
			current = next_point
		order.append(0)
		routes.append(order)
	return {"routes": routes, "engine": "heuristic"}

@router.get("/stores")
def get_stores():
	return STORES

@router.get("/products")
def get_products():
	return PRODUCTS

@router.get("/pricing/raw")
def get_prices_raw():
	return {"local": data_store.local_prices, "online": data_store.online_prices}

@router.get("/data/reset")
def data_reset():
	data_store.reset()
	return {"status": "reset"}

@router.get("/report/pdf")
def generate_pdf_report():
	buffer = BytesIO()
	c = canvas.Canvas(buffer, pagesize=A4)
	width, height = A4
	c.setFont("Helvetica-Bold", 14)
	c.drawString(40, height - 40, "Weekly Insights Report")
	c.setFont("Helvetica", 10)

	# Add pricing deltas
	y = height - 80
	c.drawString(40, y, "Pricing Comparison (Local - Online):")
	y -= 16
	for p in PRODUCTS:
		pid = p["id"]
		lp = data_store.local_prices[pid]
		op = data_store.online_prices[pid]
		delta = round(lp - op, 2)
		c.drawString(60, y, f"{pid}: local={lp}, online={op}, delta={delta}")
		y -= 14

	c.showPage()
	c.save()
	pdf = buffer.getvalue()
	buffer.close()
	return Response(content=pdf, media_type="application/pdf")
