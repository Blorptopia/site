function serializeCsv(rows, columns) {
	const lines = [
		columns,
		...rows.map(row => columns.map(key => row[key]))
	];
	return lines.map(serializeValues).join("\n");
}
function serializeValues(values) {
	return values.join(",");
}

const output = serializeCsv([
	{
		name: "Skinner",
		food: "Steamed hams"
	},
	{
		name: "Chalmers",
		food: "Hamburgers"
	}
]);
