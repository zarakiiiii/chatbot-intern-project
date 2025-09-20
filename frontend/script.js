const API_BASE = "http://127.0.0.1:8000/api";

const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');

function addMsg(text, who) {
	const div = document.createElement('div');
	div.className = `msg ${who}`;
	div.textContent = text;
	messagesEl.appendChild(div);
	messagesEl.scrollTop = messagesEl.scrollHeight;
}

addMsg("Hi! Try: 'offers', 'pricing', 'forecast', 'expiry', 'routes'", 'bot');

async function handleCommand(text) {
	const t = text.trim().toLowerCase();
	try {
		if (t === 'offers') {
			const r = await fetch(`${API_BASE}/offers`);
			const data = await r.json();
			addMsg(`Found ${data.length} offers. Example: ${data[0].description}`, 'bot');
			return;
		}
		if (t === 'pricing') {
			const r = await fetch(`${API_BASE}/pricing/compare`);
			const data = await r.json();
			const first = data[0];
			addMsg(`Pricing sample for ${first.product_id}: local=${first.local_price}, online=${first.online_price}`, 'bot');
			return;
		}
		if (t === 'forecast') {
			const body = { stores: ["store_1","store_2","store_3","store_4","store_5"], products: ["rice","wheat","sugar"], horizon_days: 7 };
			const r = await fetch(`${API_BASE}/forecast`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
			const data = await r.json();
			addMsg(`Forecasts generated: ${data.forecasts.length}`, 'bot');
			return;
		}
		if (t === 'expiry') {
			const r = await fetch(`${API_BASE}/inventory/expiry_reorder`);
			const data = await r.json();
			const risky = data.insights.filter(x => x.expiry_risk).length;
			addMsg(`Expiry risk items: ${risky}. Example reorder point: ${data.insights[0].reorder_point}`, 'bot');
			return;
		}
		if (t === 'routes') {
			const body = { vehicle_count: 3, depot_lat: 28.6139, depot_lng: 77.2090, stops: Array.from({length: 10}, (_,i)=>({ order_id: `o${i+1}`, lat: 28.6 + Math.random()*0.1, lng: 77.2 + Math.random()*0.1, service_time_min: 5 })) };
			const r = await fetch(`${API_BASE}/routing/optimize`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
			const data = await r.json();
			addMsg(`Optimized ${data.routes.length} routes`, 'bot');
			return;
		}
		addMsg("Unknown command. Try: offers, pricing, forecast, expiry, routes", 'bot');
	} catch (e) {
		addMsg(`Error: ${e.message}`, 'bot');
	}
}

sendBtn.addEventListener('click', () => {
	const text = inputEl.value;
	if (!text) return;
	addMsg(text, 'user');
	inputEl.value = '';
	handleCommand(text);
});

inputEl.addEventListener('keydown', (e) => {
	if (e.key === 'Enter') {
		sendBtn.click();
	}
});
