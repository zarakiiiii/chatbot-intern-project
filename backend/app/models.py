from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class InventoryUpdateRequest(BaseModel):
	store_id: str
	product_id: str
	quantity_delta: int = Field(..., description="Positive to add, negative to deduct")

class DeliveryBookingRequest(BaseModel):
	order_id: str
	store_id: str
	address: str
	items: Dict[str, int]

class CreditScoreRequest(BaseModel):
	retailer_id: str

class RouteStop(BaseModel):
	order_id: str
	lat: float
	lng: float
	service_time_min: int = 5

class RouteOptimizationRequest(BaseModel):
	vehicle_count: int = 3
	depot_lat: float
	depot_lng: float
	stops: List[RouteStop]

class ForecastRequest(BaseModel):
	stores: List[str]
	products: List[str]
	horizon_days: int = 14

class PricingCompareResponse(BaseModel):
	product_id: str
	local_price: float
	online_price: float
	delta: float

class PDFReportRequest(BaseModel):
	title: Optional[str] = "Weekly Insights Report"
