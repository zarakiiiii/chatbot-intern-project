import requests
import pandas as pd
import streamlit as st

API_BASE = "https://chatbot-intern-project.onrender.com/api";

st.set_page_config(page_title="Data Intelligence Dashboard", layout="wide")
st.title("Data Intelligence Dashboard")


def get_json_safe(url: str, method: str = "GET", json: dict | None = None):
	try:
		if method == "GET":
			resp = requests.get(url, timeout=5)
		else:
			resp = requests.post(url, json=json or {}, timeout=10)
		resp.raise_for_status()
		return resp.json()
	except Exception as e:
		st.error(f"Failed to fetch {url}: {e}")
		return None

col1, col2 = st.columns(2)

with col1:
	st.subheader("Offers")
	offers = get_json_safe(f"{API_BASE}/offers")
	if offers is not None:
		st.write(pd.DataFrame(offers).head())

	st.subheader("Pricing Comparison")
	pricing = get_json_safe(f"{API_BASE}/pricing/compare")
	if pricing is not None:
		st.write(pd.DataFrame(pricing))

with col2:
	st.subheader("Forecast (7 days)")
	stores = ["store_1","store_2","store_3","store_4","store_5"]
	products = ["rice","wheat","sugar"]
	forecast_payload = {"stores": stores, "products": products, "horizon_days": 7}
	forecast_res = get_json_safe(f"{API_BASE}/forecast", method="POST", json=forecast_payload)
	if forecast_res is not None:
		df_f = pd.DataFrame(forecast_res.get("forecasts", []))
		st.write(df_f.head())

st.subheader("Expiry Risk & Reorder")
insights_res = get_json_safe(f"{API_BASE}/inventory/expiry_reorder")
if insights_res is not None:
	st.write(pd.DataFrame(insights_res.get("insights", [])))

st.subheader("Route Optimization (example)")
if st.button("Optimize 10 orders"):
	stops = [{"order_id": f"o{i+1}", "lat": 28.6 + i*0.003, "lng": 77.2 + i*0.003, "service_time_min": 5} for i in range(10)]
	r = get_json_safe(f"{API_BASE}/routing/optimize", method="POST", json={"vehicle_count": 3, "depot_lat": 28.6139, "depot_lng": 77.2090, "stops": stops})
	if r is not None:
		st.json(r)

st.subheader("PDF Report")
if st.button("Generate PDF"):
	try:
		pdf = requests.get(f"{API_BASE}/report/pdf", timeout=20).content
		st.download_button("Download Report", data=pdf, file_name="insights_report.pdf")
	except Exception as e:
		st.error(f"Failed to generate PDF: {e}")
