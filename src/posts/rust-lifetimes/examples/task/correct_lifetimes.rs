//! Your goal for this task is to add lifetimes to [`swap_arguments`] to make the program compile.
//! You should not touch anything else.

/// This function should swap the arguments given
/// So it should convert from
/// (fruit, game) to
/// (game, fruit)
fn swap_arguments<'first, 'second>(
    fruit: &'first str,
    game: &'second str
) -> (&'second str, &'first str) {
	(game, fruit)
}

fn main() {
    let fruit = "Mango".to_string();
    let output_fruit = {
        let game = "Quake".to_string();
        
        let (output_game, output_fruit) = swap_arguments(&fruit, &game);
        assert_eq!(game, output_game);
        
        output_fruit
    };
    
    assert_eq!(fruit, output_fruit);
}

