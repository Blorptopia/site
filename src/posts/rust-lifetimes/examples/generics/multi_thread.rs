fn print_on_secondary_thread<TextT: AsRef<str> + Send + Sync + 'static>(text: TextT) {
	std::thread::spawn(move || {
		let as_str = text.as_ref();
		println!("{as_str} from another thread");
	});
}
fn main() {
	// This allows passing both a &'static str
	print_on_secondary_thread("hi");

	let owned = "hello".to_string();

	// A reference to a String does not work
	// print_on_secondary_thread(&owned);

	// and an owned string itself
	print_on_secondary_thread(owned);
}
