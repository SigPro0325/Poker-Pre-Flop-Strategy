import random
import itertools
total_cards_in_deck = 52

def chen_formula(hole_cards):
    card_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    ranks = [card[0] for card in hole_cards]
    suits = [card[1] for card in hole_cards]
    values = [card_values[rank] for rank in ranks]

    score = max(values) / 2  # Start with the highest card value halved to dial down aggression

    # Adjustments for card pairing, suitedness, and gaps
    if ranks[0] == ranks[1]:  # Pairing
        score *= 2
        if score < 5: score = 5
    if suits[0] == suits[1]:  # Suitedness
        score += 2
    gap = abs(values[0] - values[1]) - 1
    if gap in [1, 2]: score -= gap
    elif gap > 2: score -= 4
    if gap == 1 and ('A' in ranks or '5' in ranks): score += 1  # Adjustment for A-5 straight potential

    return score

def determine_aggression_factor(tournament_stage, current_round, total_rounds, position):
    base_aggression = 0.5 if tournament_stage in ['early', 'stage1', 'stage2'] else 1.0
    if position in ['early']:
        base_aggression *= 0.8  # Dial down aggression in early position
    round_factor = current_round / total_rounds
    if round_factor < 0.5:
        return base_aggression * 0.9
    else:
        return base_aggression * 1.1
    

def get_raise_threshold(hand_strength, position, aggression_factor):
    if position in ['early']:
        return max(0.7, hand_strength * aggression_factor)  # Higher threshold for early position
    else:
        return max(0.6, hand_strength * aggression_factor)  # Standard threshold for other positions

def evaluate_hand_strength(hole_cards, position, tournament_stage, round_number, total_rounds):
    # Calculates basic hand strength using the Chen Formula
    basic_strength = chen_formula(hole_cards)

    # Adjustments for tournament stage and round
    stage_adjustment = get_stage_adjustment(tournament_stage)
    round_adjustment = get_round_adjustment(round_number, total_rounds)

    # Introduces a positional adjustment to scale hand strength based on position
    # Early positions have a multiplier less than 1 to reduce hand strength,
    # while late positions have a multiplier slightly greater than 1 to increase hand strength.
    if position in ['early', 'middle']:
        positional_adjustment = 0.9  # Conservative play in early and middle positions
    elif position in ['late', 'blinds']:
        positional_adjustment = 1.1  # More aggressive play in late positions and blinds
    else:
        positional_adjustment = 1.0  # Neutral adjustment for undefined positions

    # Combines all adjustments to calculate final hand strength
    final_strength = basic_strength * stage_adjustment * round_adjustment * positional_adjustment

    return final_strength

def calculate_adaptive_raise(min_amount, max_amount, adjusted_hand_strength, spr, position, tournament_stage, round_number, total_rounds, opponent_profiles, stack_size):
    """
    Calculates an adaptive raise amount based on various factors including hand strength, SPR, position,
    tournament progression, and opponent tendencies.
    """
    # Initial base percentage of stack to use for raise amount, influenced by hand strength and round progression
    base_percentage = 0.02 + adjusted_hand_strength * 0.03 + (round_number / total_rounds) * 0.02

    # Adjusting base percentage based on SPR, position, and tournament stage
    if spr < 10:
        base_percentage *= 0.8  # Tighter play with low SPR
    elif spr > 20:
        base_percentage *= 1.2  # Looser play with high SPR

    if position in ['late', 'blinds']:
        base_percentage *= 1.1  # More aggressive in favorable positions

    if tournament_stage == 'final':
        base_percentage *= 1.2  # Increase aggression in final stages

    # Adjusting for opponent profiles
    if any(profile['tendency'] == 'tight' for profile in opponent_profiles.values()):
        base_percentage *= 1.1
    elif any(profile['tendency'] == 'loose' for profile in opponent_profiles.values()):
        base_percentage *= 0.9

    # Calculates final raise amount based on adjusted base percentage of the stack size, ensuring it's within bounds
    final_raise_amount = max(min_amount, min(stack_size * base_percentage, max_amount))

    # Rounds the final raise amount to the nearest whole number
    final_raise_amount = round(final_raise_amount)

    return final_raise_amount

def get_stage_adjustment(tournament_stage):
    adjustments = {
        'early': 1.0,  # Standard play in early rounds
        'middle': 1.05,  # Slightly more aggressive in middle stages
        'final': 1.1,  # Most aggressive in final stages
    }
    return adjustments.get(tournament_stage, 1.0)

def get_round_adjustment(round_number, total_rounds):
    progression_factor = round_number / total_rounds
    if progression_factor < 0.5:
        return 0.95  # More conservative in the first half
    else:
        return 1.05
    
def get_stack_adjustment(stack_size, blinds):
    stack_to_blind_ratio = stack_size / blinds
    if stack_to_blind_ratio < 10:
        return 0.8
    elif stack_to_blind_ratio > 50:
        return 1.2
    return 1.0

def get_opponent_adjustment(opponent_profiles):
    # Example: Adjust based on the number of aggressive vs. passive opponents
    aggressive = sum(1 for profile in opponent_profiles.values() if profile['tendency'] == 'aggressive')
    passive = sum(1 for profile in opponent_profiles.values() if profile['tendency'] == 'passive')
    if aggressive > passive:
        return 1.05  # More aggressive play against aggressive opponents
    else:
        return 0.95
    
def determine_hand_group_pre_flop(hand_str):
    # Defines card rank and suit for both cards
    rank1, suit1, rank2, suit2 = hand_str[0], hand_str[1], hand_str[2], hand_str[3]
    suited = suit1 == suit2

    # Defines rank categories
    premium_ranks = 'AKQ'
    high_ranks = 'JT'
    mid_ranks = '987'
    low_ranks = '65432'

    # Checks for high-low combinations and suitedness
    high_low_suited = (rank1 in premium_ranks and rank2 in low_ranks) or (rank2 in premium_ranks and rank1 in low_ranks)

    # Blocker effects
    has_ace_blocker = 'A' in hand_str
    has_king_blocker = 'K' in hand_str

    # Suited hand classifications
    if suited:
        if high_low_suited:
            return "High-Low Suited"
        elif rank1 in premium_ranks and rank2 in premium_ranks:
            return "Premium Suited"
        elif rank1 in premium_ranks or rank2 in premium_ranks:
            return "Suited with High Card"
        elif rank1 in high_ranks and rank2 in high_ranks:
            return "High Suited Connectors"
        elif rank1 in mid_ranks and rank2 in mid_ranks:
            return "Mid Suited Connectors"
        elif rank1 in low_ranks and rank2 in low_ranks:
            return "Low Suited"
        else:
            return "Miscellaneous Suited"

    # Offsuit hand classifications
    else:
        if has_ace_blocker:
            if rank1 == 'A' and rank2 in high_ranks or rank2 == 'A' and rank1 in high_ranks:
                return "Ace Blocker with High Card"
            return "Ace Blocker"
        elif has_king_blocker:
            if rank1 == 'K' and rank2 in high_ranks or rank2 == 'K' and rank1 in high_ranks:
                return "King Blocker with High Card"
            return "King Blocker"
        elif rank1 in premium_ranks and rank2 in premium_ranks:
            return "Premium Offsuit"
        elif rank1 in high_ranks and rank2 in high_ranks:
            return "High Offsuit Connectors"
        elif rank1 in mid_ranks and rank2 in mid_ranks:
            return "Mid Offsuit Connectors"
        elif rank1 in premium_ranks or rank2 in premium_ranks:
            return "Offsuit with High Card"
        elif rank1 in low_ranks and rank2 in low_ranks:
            return "Low Offsuit"
        else:
            return "Miscellaneous Offsuit"

    # Default classification for non-specific hands
    return "Standard Offsuit"

def adjust_for_opponent_profiles(ai_opponent_profiles, position, tournament_stage):
    adjustment_factor = 1.0
    for profile in ai_opponent_profiles.values():
        if profile['tendency'] == 'tight':
            adjustment_factor += 0.05
        elif profile['tendency'] == 'loose':
            adjustment_factor -= 0.05
    # Further adjustments can be based on position and tournament_stage if needed
    return adjustment_factor

def get_game_stage_adjustment(tournament_stage, stack_size, blinds):
    # Example placeholder logic 
    if tournament_stage in ['early', 'stage1', 'stage2']:
        return 0.9 if stack_size / blinds > 20 else 1.1
    else:
        return 1.2  # More aggressive in later stages
    
def estimate_win_probability_single_hand(hand, number_of_opponents, position, tournament_phase, stack_size, average_stack):
    # Advanced hand groupings
    hand_str = "".join(str(card) for card in hand)
    hand_strength = evaluate_hand_strength(hand_str)  # Corrected call
    hand_group = determine_hand_group_pre_flop(hand_str)

    # Base probabilities for advanced hand groups
    hand_group_probabilities = {
        "Premium Suited Connectors": 0.85,
        "High-Low Suited": 0.65,
        "Ace Blocker": 0.60,
        "King Blocker": 0.55,
        "Premium Suited": 0.80,
        "Suited with High Card": 0.70,
        "High Suited Connectors": 0.75,
        "Mid Suited Connectors": 0.60,
        "Low Suited": 0.50,
        "Miscellaneous Suited": 0.55,
        "Premium Offsuit": 0.75,
        "High Offsuit Connectors": 0.70,
        "Mid Offsuit Connectors": 0.60,
        "Offsuit with High Card": 0.65,
        "Low Offsuit": 0.45,
        "Miscellaneous Offsuit": 0.50,
        "Standard Offsuit": 0.40,
        "Trash": 0.30,
    }

    base_probability = hand_group_probabilities.get(hand_group, 0.1)

    # Adjusts probability based on the number of opponents
    if number_of_opponents > 2:
        base_probability *= (1 - 0.05 * (number_of_opponents - 2))

    # Adjusts probability for player position
    position_modifier = {"early": 0.9, "middle": 0.95, "late": 1.05, "blinds": 1.0}
    base_probability *= position_modifier.get(position, 1.0)

    # Tournament phase adjustments
    tournament_phase_modifier = {"early": 1.0, "middle": 1.05, "bubble": 2.0, "final": 0.9}
    base_probability *= tournament_phase_modifier.get(tournament_phase, 1.0)

    # Stack size adjustments
    if stack_size < average_stack / 2:
        base_probability *= 0.9  # Tighten up with a short stack
    elif stack_size > average_stack * 2:
        base_probability *= 1.1  # Loosen up with a big stack

    return base_probability

def estimate_win_probability_ai(hole_card, position, ai_opponent_profiles, stack_size, pot_size, blinds, tournament_stage):
    """
    Simplified win probability estimation without specific stack adjustment.
    """
    # Converts hole cards to a string format suitable for evaluation
    hand_str = "".join(hole_card)

    # Evaluates the base strength of the hand
    hand_strength = evaluate_hand_strength(hand_str)

    # Adjusts win probability based on player position and opponent profiles
    position_adjustment = get_position_adjustment(position)
    # Adjusted function call with all required arguments
    opponent_adjustment = adjust_for_opponent_profiles(ai_opponent_profiles, position, tournament_stage)

    # Combines adjustments to estimate win probability
    win_probability = hand_strength * position_adjustment * opponent_adjustment

    return win_probability

def get_pre_flop_action(hole_card, position, ai_opponent_profiles, stack_size, pot_size, blinds, tournament_stage, current_round, total_rounds):
    min_amount = blinds
    max_amount = min(500, stack_size // 5)  # Adjusted for playability
    hand_strength = evaluate_hand_strength(hole_card, position, tournament_stage, current_round, total_rounds)
    aggression_factor = determine_aggression_factor(tournament_stage, current_round, total_rounds, position)
    raise_threshold = get_raise_threshold(hand_strength, position, aggression_factor)

    # Adjustments for opponent profiles
    opponent_adjustment = get_opponent_adjustment(ai_opponent_profiles)  # Assuming this function is correctly defined to return a multiplier based on opponent tendencies

    # SPR calculation
    spr = stack_size / max(pot_size, blinds)

    # Strategy adjustments based on the tournament stage, current round, and opponent profiles
    # This involves determining how aggressive or conservative the AI should be
    # Aggression factor could be based on the stage of the tournament and the progression through rounds
    aggression_factor = 1.0  # Placeholder, adjust based on the strategy

    # Adjusts hand strength based on aggression factor and opponent profiles
    adjusted_hand_strength = hand_strength * aggression_factor

    # Decision thresholds could also be dynamically adjusted based on tournament progression
    raise_threshold = 0.4  # Example threshold, adjust as needed
    call_threshold = 0.6  # Example threshold, adjust as needed

    position_adjustment = 1.0
    if position in ['early', 'middle']:
        position_adjustment -= 0.1  # More conservative in early and middle positions
    opponent_adjustment = adjust_for_opponent_profiles(ai_opponent_profiles, position, tournament_stage)

    game_adjustment = 1.0  # Could further refine this if we had more specific game stage logic

    # Adjusts strategy based on tournament stage and current round
    aggression_factor = 1.0  # Start with a baseline aggression factor
    if tournament_stage == 'early' and current_round <= total_rounds / 2:
        aggression_factor -= 0.2  # Less aggressive in early rounds of early stage
    elif tournament_stage in ['middle', 'final'] and current_round > total_rounds / 2:
        aggression_factor += 0.2  # More aggressive in later rounds of middle and final stages

    # Adjusts hand strength based on position and game dynamics
    adjusted_hand_strength = hand_strength * position_adjustment * opponent_adjustment * game_adjustment * aggression_factor

    # SPR to inform betting strategy
    spr = stack_size / max(pot_size, blinds)

    # Determines action based on adjusted hand strength
    if adjusted_hand_strength >= 0.7:  # Adjusting the threshold based on feedback
        action, amount = "raise", calculate_adaptive_raise(min_amount, max_amount, adjusted_hand_strength, spr, position, tournament_stage, current_round, total_rounds, ai_opponent_profiles, stack_size)

    elif adjusted_hand_strength >= 0.4:  # Providing a broader range for calling
        action, amount = "call", min_amount
    else:
        action, amount = "fold", 0

    return action, min(amount, max_amount)

def determine_risk_tolerance(tournament_stage, stack_size, blinds, average_stack, opponent_profiles):
    """
    Determines the AI's risk tolerance based on the game context.

    Args:
        tournament_stage (str): Current stage of the tournament.
        stack_size (int): The AI's current stack size.
        blinds (int): Current level of blinds.
        average_stack (int): Average stack size at the table.
        opponent_profiles (dict): The playing styles of the opponents.

    Returns:
        float: A factor representing the AI's risk tolerance.
    """
    tolerance = 1.0  # Base risk tolerance

    # Adjusts based on tournament stage
    if tournament_stage == 'early':
        tolerance *= 0.9
    elif tournament_stage == 'bubble':
        tolerance *= 0.8
    elif tournament_stage == 'final':
        tolerance *= 1.1

    # Adjusts based on stack size relative to blinds
    stack_to_blind_ratio = stack_size / blinds
    if stack_to_blind_ratio < 10:  # Short stack
        tolerance *= 0.8
    elif stack_to_blind_ratio > 50:  # Deep stack
        tolerance *= 1.2

    # Adjusts based on average stack size
    if stack_size < average_stack:
        tolerance *= 0.9

    # Adjusts based on opponents' playing styles
    tight_opponents = sum(1 for profile in opponent_profiles.values() if profile['tendency'] == 'tight')
    loose_opponents = sum(1 for profile in opponent_profiles.values() if profile['tendency'] == 'loose')

    if tight_opponents > loose_opponents:
        tolerance *= 1.1  # Increase risk tolerance against tight opponents
    elif loose_opponents > tight_opponents:
        tolerance *= 0.9  # Decrease risk tolerance against loose opponents

    return tolerance

def calculate_ev(call_pot_odds, win_probability, pot_size, stack_size):
    """
    Calculate the expected value of a hand given the current situation.

    Args:
        call_pot_odds (float): The pot odds for calling.
        win_probability (float): Probability of winning.
        pot_size (int): Current size of the pot.
        stack_size (int): Size of the player's stack.

    Returns:
        float: The expected value of the hand.
    """
    # Simplified EV calculation: (Win Probability * Pot Size) - (Loss Probability * Call Amount)
    loss_probability = 1 - win_probability
    call_amount = min(call_pot_odds * pot_size, stack_size)
    ev = (win_probability * pot_size) - (loss_probability * call_amount)
    return ev

def bluff_strategy(min_amount, max_amount, stack_size, pot_size, ai_opponent_profiles, position, tournament_stage, perceived_hand_strength, round_number, total_rounds):
    """
    Enhanced bluffing strategy that considers tournament stage, round progression, and opponent tendencies to decide on bluffing.

    Args:
        min_amount (int): Minimum bet amount.
        max_amount (int): Maximum bet amount.
        stack_size (int): Player's stack size.
        pot_size (int): Current pot size.
        ai_opponent_profiles (dict): Profiles of AI opponents' playing styles.
        position (str): Player's position.
        tournament_stage (str): Stage of the tournament.
        perceived_hand_strength (float): Perceived strength of the hand.
        round_number (int): Current round number within the tournament stage.
        total_rounds (int): Total number of rounds in the current tournament stage.

    Returns:
        tuple[str, int]: Action and amount for the bluff.
    """
    # Adjusts bluff strategy based on tournament progression
    progression_factor = round_number / total_rounds
    aggressive_play_threshold = 0.5  # Threshold for switching to more aggressive play

    # Adjusts bluff size calculation factors based on round progression
    position_factor = 1.5 if position == 'late' else 1
    strength_factor = 0.5 if perceived_hand_strength < 0.5 else 0.8
    progression_factor_adjustment = 1.2 if progression_factor > aggressive_play_threshold else 1.0

    # Calculates final bluff size with adjustments
    bluff_size = min(max_amount, max_amount * pot_factor * stack_factor * position_factor * strength_factor * progression_factor_adjustment)

    # Adjusts bluffing based on opponent tendencies and tournament stage
    bluff_adjusted = adjust_bluff_based_on_opponents_and_stage(ai_opponent_profiles, stack_size, tournament_stage, progression_factor)

    # Make the decision to bluff based on adjusted criteria
    if bluff_adjusted:
        return "raise", max(bluff_size, min_amount)
    else:
        return "fold", 0

def adjust_bluff_based_on_opponents_and_stage(ai_opponent_profiles, stack_size, tournament_stage, progression_factor):
    """
    Adjusts the decision to bluff based on opponent profiles, tournament stage, and round progression.

    Args:
        ai_opponent_profiles (dict): Profiles of AI opponents' playing styles.
        stack_size (int): Player's stack size.
        tournament_stage (str): Stage of the tournament.
        progression_factor (float): Progression through the current tournament stage as a fraction.

    Returns:
        bool: Indicates whether the bluff has been adjusted (True) or not (False).
    """
    bluff_adjusted = False
    for profile in ai_opponent_profiles.values():
        if profile['tendency'] == 'tight' and stack_size > profile.get('stack_size', stack_size):
            bluff_adjusted = True
            break
        elif profile['tendency'] == 'loose' and stack_size < profile.get('stack_size', stack_size):
            bluff_adjusted = True
            break

    # Further adjustments for tournament stage and round progression
    if tournament_stage == 'early' and progression_factor < 0.5:
        bluff_adjusted = False  # Less likely to bluff in early rounds
    elif tournament_stage == 'final' and progression_factor > 0.5:
        bluff_adjusted = True  # More likely to bluff in later rounds of the final stage

    return bluff_adjusted

def should_bluff(position, opponent_profiles, tournament_stage, round_number, total_rounds):
    """
    Determines if the AI should attempt a bluff given the current situation, with adjustments for tournament progression.

    Args:
        position (str): Player's position.
        opponent_profiles (dict): AI opponents' profiles.
        tournament_stage (str): Stage of the tournament.
        round_number (int): The current round number within the tournament stage.
        total_rounds (int): The total number of rounds in the current tournament stage.

    Returns:
        bool: True if a bluff should be attempted, False otherwise.
    """
    # Calculates progression factor to dynamically adjust bluffing strategy
    progression_factor = round_number / total_rounds
    late_stage = tournament_stage in ['final']
    early_or_mid_stage = tournament_stage in ['early', 'middle']
    late_position = position in ['late', 'blinds']
    aggressive_play_threshold = 0.5  # Threshold for more aggressive play in later rounds

    # Adjusts bluffing probability based on position and tournament stage
    bluff_probability = 0.7  # Base probability to bluff #To be ADJUSTABLE

    # Increase bluffing probability in late positions or specific tournament stages
    if late_position:
        bluff_probability += 0.1  # More likely to bluff in late position #To be ADJUSTABLE

    if late_stage and progression_factor > aggressive_play_threshold:
        bluff_probability += 0.2  # More aggressive bluffing in the final stages of the tournament

    elif early_or_mid_stage and progression_factor < aggressive_play_threshold:
        bluff_probability -= 0.1  # Less likely to bluff in early rounds # To be ADJUSTABLE

    # Consider opponent profiles for adjusting bluffing strategy
    if any(profile['tendency'] == 'tight' for profile in opponent_profiles.values()):
        bluff_probability += 0.1  # Increase bluffing against tight players

    if any(profile['tendency'] == 'aggressive' for profile in opponent_profiles.values()):
        bluff_probability -= 0.1  # Decrease bluffing against aggressive players

    # Makes the final decision to bluff based on the adjusted probability
    return random.random() < bluff_probability

def calculate_bluff_size_factor(pot_size, opponent_profiles, position, tournament_stage):
    """
    Calculate the size factor for a bluff.

    Args:
        pot_size (int): Current pot size.
        opponent_profiles (dict): Profiles of opponents' playing styles.
        position (str): Player's position.
        tournament_stage (str): Stage of the tournament.

    Returns:
        float: Bluff size factor.
    """
    # Example logic for bluff size factor
    factor = 0.1  # Starting factor
    if position in ['late', 'blinds']:
        factor += 0.05
    if tournament_stage == 'middle':
        factor += 0.05
    # Adjust factor based on opponent tendencies
    if any(profile['tendency'] == 'tight' for profile in opponent_profiles.values()):
        factor += 0.05
    return factor

def should_attempt_bluff(opponent_profiles, position, table_image, pot_size, tournament_stage):
    """
    Decide whether to attempt a bluff based on advanced poker strategies.

    Args:
        opponent_profiles (dict): Profiles of opponents' playing styles.
        position (str): Player's position.
        table_image (str): Player's current table image (e.g., 'tight', 'loose', 'aggressive').
        pot_size (int): Current pot size.
        tournament_stage (str): Stage of the tournament.

    Returns:
        bool: True if a bluff should be attempted, False otherwise.
    """
    # Analyses opponents for bluffing potential
    bluff_opportunity = any(profile['tendency'] == 'tight' for profile in opponent_profiles.values())

    # More likely to bluff if the AI has a tight table image
    if table_image == 'tight':
        bluff_opportunity = bluff_opportunity and random.random() < 0.6

    # Adjusts bluffing based on position
    if position in ['late', 'blinds']:
        bluff_opportunity = bluff_opportunity and random.random() < 0.5

    # Consider pot size and number of player

    return bluff_opportunity

def make_exploitative_decision(max_amount, pre_flop_probability, opponent_profiles, spr, position, stack_size, average_stack):
    """
    Make a decision based on exploiting opponent weaknesses, considering various factors.

    Args:
        max_amount (int): Maximum bet amount.
        pre_flop_probability (float): Estimated probability of winning pre-flop.
        opponent_profiles (dict): Profiles of the opponents.
        spr (float): Stack-to-pot ratio.
        position (str): Player's position.
        stack_size (int): Player's stack size.
        average_stack (int): Average stack size at the table.

    Returns:
        tuple[str, int]: Action and amount.
    """
    aggressive_opponents = any(profile['tendency'] == 'aggressive' for profile in opponent_profiles.values())
    passive_opponents = any(profile['tendency'] == 'passive' for profile in opponent_profiles.values())

    # Adjusts decision based on opponents' tendencies
    if passive_opponents:
        if pre_flop_probability > 0.6 and spr > 10:
            raise_amount = min(max_amount, max_amount / 2)
            return "raise", raise_amount
        else:
            call_amount = max_amount / 4
            return "call", call_amount
    elif aggressive_opponents:
        if pre_flop_probability > 0.5:
            # More conservative play against aggressive opponents
            call_amount = max_amount / 4 if position in ['late', 'blinds'] else 0
            return "call", call_amount
        else:
            return "fold", 0
    else:
        # Default strategy for mixed or unknown opponent tendencies
        if pre_flop_probability > 0.7 and spr > 15:
            return "raise", min(max_amount, max_amount / 2)
        elif pre_flop_probability > 0.4:
            return "call", max_amount / 4
        else:
            return "fold", 0

    # Stack size adjustments
    if stack_size < average_stack / 2:
        # Tighten up with a short stack
        return "call" if pre_flop_probability > 0.5 else "fold", max_amount / 4
    elif stack_size > average_stack * 2:
        # Loosen up with a big stack
        return "raise", min(max_amount, max_amount / 2) if pre_flop_probability > 0.4 else "call", max_amount / 4

    return "fold", 0

def make_gto_decision(min_amount, max_amount, position, spr, tournament_stage, round_number, total_rounds, opponent_profiles, adjusted_hand_strength):
    """
    Makes a decision based on a Game Theory Optimal (GTO) approach, considering position, SPR,
    the stage of the tournament, round progression, opponent tendencies, and adjusted hand strength.

    Args:
        min_amount (int): Minimum bet amount.
        max_amount (int): Maximum bet amount.
        position (str): Player's position at the table.
        spr (float): Stack-to-pot ratio.
        tournament_stage (str): Current stage of the tournament.
        round_number (int): Current round number within the tournament stage.
        total_rounds (int): Total number of rounds in the current tournament stage.
        opponent_profiles (dict): Profiles of the opponents.
        adjusted_hand_strength (float): Adjusted strength of the hand based on various factors.

    Returns:
        tuple: A tuple of the action ('raise', 'call', 'fold') and the amount.
    """
    # Adjusts weights for action choices based on various factors
    raise_weight, call_weight, fold_weight = 0.3, 0.4, 0.3
    if position in ['late', 'blinds']:
        raise_weight += 0.1
        call_weight += 0.1

    # Adjusts for tournament stage and round progression
    progression_factor = round_number / total_rounds
    if tournament_stage == 'final' and progression_factor > 0.5:
        raise_weight += 0.2  # More aggressive in final stages
    elif tournament_stage == 'early' and progression_factor < 0.5:
        fold_weight += 0.2  # More conservative in early stages

    # Adjusts based on SPR
    if spr < 10:
        fold_weight += 0.1  # More conservative with low SPR
    elif spr > 20:
        raise_weight += 0.1  # More aggressive with high SPR

    # Adjusts based on adjusted hand strength
    if adjusted_hand_strength > 0.8:
        raise_weight += 0.2
    elif adjusted_hand_strength < 0.4:
        fold_weight += 0.2

    # Normalize weights
    total_weight = raise_weight + call_weight + fold_weight
    raise_weight /= total_weight
    call_weight /= total_weight
    fold_weight /= total_weight

    # Makes decision
    action_choice = random.choices(['raise', 'call', 'fold'], weights=[raise_weight, call_weight, fold_weight], k=1)[0]

    # Determines amount for raise action
    if action_choice == 'raise':
        raise_amount = calculate_adaptive_raise(min_amount, max_amount, adjusted_hand_strength, spr, position, tournament_stage, round_number, total_rounds, opponent_profiles, max_amount)
        return "raise", raise_amount
    elif action_choice == 'call':
        return "call", min_amount
    else:
        return "fold", 0

#TESTING THE ABOVE LOGIC
import random

# Defines card ranks and suits
cards = ['A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'K', 'Q']
suits = ['C', 'H', 'D', 'S']

# Randomly select two distinct cards for the AI's hand
selected_cards = random.sample(cards, 2)
selected_suit = random.choice(suits)
hole_card = [selected_cards[0] + selected_suit, selected_cards[1] + random.choice(suits)]

# Defines additional parameters for the get_pre_flop_action function
position = 'early'  # Example position
ai_opponent_profiles = {'11SR': {'tendency': 'passive'}}  # Example opponent profile
stack_size = 1000  # Example stack size
pot_size = 100 # Example pot size
blinds = 10  # Example blinds
tournament_stage = 'early'  # Example tournament stage
average_stack = 3000  # Example average stack size

# New parameters for enhanced testing
current_round = 10 # Example current round number # TO BE TESTED 
total_rounds = 20  # Example total rounds in the current tournament stage #TO BE TESTED

# Adapted call to get_pre_flop_action including new parameters
pre_flop_action = get_pre_flop_action(hole_card, position=position, ai_opponent_profiles=ai_opponent_profiles, stack_size=stack_size, pot_size=pot_size, blinds=blinds,  tournament_stage=tournament_stage, current_round=current_round, total_rounds=total_rounds)

print(f"Hole Card: {hole_card}, Action: {pre_flop_action}")













