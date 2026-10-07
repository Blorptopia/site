fn print_on_secondary_thread<TextT: AsRef<str> + Send + Sync>(text: TextT) {
	//                                                        ^^^^
	//                                text may not live long enough
	std::thread::spawn(move || {
		let as_str = text.as_ref();
		println!("{as_str} from another thread");
	});
}
fn main() {
	// This allows passing both a &'static str
	print_on_secondary_thread("hi");

	let owned = "hello".to_string();

	// A reference to a String
	print_on_secondary_thread(&owned);

	// and an owned String itself
	print_on_secondary_thread(owned);
}
