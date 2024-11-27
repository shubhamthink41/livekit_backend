import re


CHARACTER_NAMES = ["emma wilson", "emma", "host",
                   "jane porter", "jane", "michael brooks", "michael"]


def get_character_switch_patterns(char_name):
    """
    Generate comprehensive regex patterns for switching to a character

    Args:
        char_name (str): Name of the character to match

    Returns:
        str: Regex pattern for character switch
    """
    patterns = [
        # Direct requests
        fr"(okay I want talk to {re.escape(char_name)}|"
        fr"i want to {re.escape(char_name)}|"

        # Conversational variations
        fr"can you switch to {re.escape(char_name)}|"
        fr"change to {re.escape(char_name)}|"
        fr"let me talk to {re.escape(char_name)}|"

        # Polite requests
        fr"would you mind changing to {re.escape(char_name)}?|"
        fr"could you switch to {re.escape(char_name)}|"

        # Excited or emphatic requests
        fr"hey, I really want to talk to {re.escape(char_name)}!|"
        fr"switch now to {re.escape(char_name)}!|"

        # Contextual requests
        fr"bring out {re.escape(char_name)}|"
        fr"activate {re.escape(char_name)}|"
        fr"i'd like to speak with {re.escape(char_name)}|"

        # Casual conversational
        fr"yo, {re.escape(char_name)}|"
        fr"hey {re.escape(char_name)}|"

        # With additional context
        fr"can we have {re.escape(char_name)} take over|"
        fr"time for {re.escape(char_name)} to jump in)"
    ]

    return '|'.join(patterns)


def get_character_voice_map():
    """
    Map characters to specific voices.

    Returns:
        dict: Mapping of character names to TTS voices.
    """
    return {
        "emma wilson": "alloy",
        "emma": "alloy",
        "host": "echo",
        "jane porter": "shimmer",
        "jane": "shimmer",
        "michael brooks": "onyx",
        "michael": "onyx"
    }


voices = {
    "emma wilson": "alloy",
    "emma": "alloy",
    "host": "echo",
    "jane porter": "Shimmer",
    "jane": "Shimmer",
    "michael brooks": "onyx",
    "michael": "onyx"
}

def extract_character_data(story_json):

    voice_map_by_gender = {
        "female": ["alloy", "shimmer"],
        "male": ["onyx", "echo"]
    }

    character_names = []
    voice_map = {}
    voice_index = {"female": 0, "male": 0}  

    for character in story_json.get("characters", []):
        name = character["name"].lower()
        short_name = name.split()[0].lower()
        gender = character.get("gender", "").lower()

        character_names.extend([name, short_name])

        if gender in voice_map_by_gender:
            voices = voice_map_by_gender[gender]
            voice = voices[voice_index[gender] % len(voices)]
            voice_map[name] = voice
            voice_map[short_name] = voice
            voice_index[gender] += 1
        else:
            voice_map[name] = "default_voice"
            voice_map[short_name] = "default_voice"

    character_names.append("host")
    voice_map["host"] = "fable"

    return character_names, voice_map


