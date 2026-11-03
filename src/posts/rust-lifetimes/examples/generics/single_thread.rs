fn print_text<TextT: AsRef<str>>(text: TextT) {
	let as_str = text.as_ref();
	println!("{as_str}");
}
fn main() {
	// This allows passing both a &'static str
	print_text("hi");

	let owned = "hello".to_string();

	// A reference to a string
	print_text(&owned);

	// and an owned string itself
	print_text(&owned);
}
