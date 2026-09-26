const ws = new WebSocket("/ws");
ws.addEventListener("error", () => {
	console.log("[LIVE RELOAD] WS error detected, reloading");
	location.reload();
});
ws.addEventListener("close", () => {
	console.log("[LIVE RELOAD] WS close detected, reloading");
	location.reload();
});
