fn reference_to<'a>(param: &'a str) -> &'a str {
	param
}

fn main() {
	let text = "hi".to_string();
	let reference = reference_to(&text);
	println!("text from reference: {reference}");
}
