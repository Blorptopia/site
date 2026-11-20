// Poll based
const workerPool = new WorkerPool({
	poll: () => {
		return remainingTasks.pop() ?? null;
	}
	...
});
workerPool.startPolling();

// AsyncIterator based
const workerPool = new WorkerPool({
	stream: async function*() {
		while (true) {
			const task = remainingTasks.pop();
			if (task === undefined) {
				break;
			}
			yield task;
		}
	}
});
