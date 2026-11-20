export function escapeValue(text) {
	if (
		text.includes("\n") ||
		text.includes("\"") ||
		text.includes(",")
	) {
		const escapedText = text.replaceAll("\"", "\"\"");
		return `"${escapedText}"`;
	} else {
		return text;
	}
}
