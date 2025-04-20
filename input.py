# https://aistudio.google.com/apikey

MODEL_NAME = 'gemini-2.0-flash' # Or 'gemini-1.5-flash-latest' OR 'gemini-1.5-pro-latest'

INPUT_IMAGE_FOLDER = "Data"

OUTPUT_TEMP_FOLDER = "Data/Temp"

OUTPUT_IMAGE_FOLDER = "Data/Final_Output"

STAT_CATEGORIES = ["Stats_Shooting", "Stats_Possession", "Stats_Passing", "Stats_Goalkeeping", "Stats_Defending","Stats_Summary"]

GEMINI_PROMPT = """
Analyze the provided image, which displays player performance statistics from a football game simulation (like FIFA or EA FC).

Extract the data according to the following structure and return it STRICTLY as a single JSON object.
Do not include any explanatory text, markdown formatting (like ```json), or comments before or after the JSON block itself.

Desired JSON Structure:
{
    "team_name": "string", // Found top right
    "featured_player": { // Found top left box
        "name": "string",
        "overall_rating": integer, // OVR
        "match_rating": float // Rating next to name
    },
    "player_list": [ // Found in the left table
        {
        "position": "string", // POS
        "name": "string",
        "match_rating": float, // MR
        "goals": integer, // G
        "assists": integer // AST
        }
        // ... include all players listed
    ],
    "detailed_stats_category": "string", // Found in the top menu tabs (selected one, e.g., "Summary", "Shooting", "Passing", "Possession", "Defending", "Goalkeeping")
    "selected_player_detailed_stats": { // Data from the right panel, corresponds to highlighted player in left table.
        "player_name": "string", // Name of the highlighted player from the left table (e.g., Hleb)
        "stats": {
            // Key-value pairs from the right panel stats list.
            // If the "detailed_stats_category" is "Summary", extract the first value for each stat.
            // If the "detailed_stats_category" is "Goalkeeping" OR any other single-column category ("Shooting", "Passing", "Possession", "Defending"), extract the single value present for each stat as the player's stat.
            // If the "detailed_stats_category" is "Passing" or "Possession", and there is a visible "Line Breaks" section with "Through Attempted", "Through Completed", "Around Attempted", "Around Completed", "Over Attempted", or "Over Completed" stats under "Forward Line Breaks", "Midfield Line Breaks", or "Defensive Line Breaks" headers, then:
            //   - For each visible stat under "Forward Line Breaks", prefix the key with "Forward ".
            //   - For each visible stat under "Midfield Line Breaks", prefix the key with "Midfield ".
            //   - For each visible stat under "Defensive Line Breaks", prefix the key with "Defensive ".
            //   - Only extract line break stats if their corresponding "Forward Line Breaks", "Midfield Line Breaks", or "Defensive Line Breaks" header is visible in the image directly above them. Do not extract line break stats AT ALL if their header is not visible ABOVE THEM. Do not extract anything if only header is visible.
            // Example (Summary): "Goals": 1, "Shot Accuracy (%)": 75, ... etc.
            // Example (Possession): "Possession (%)": 7, "Dribbles": 19, "Forward Through Attempted": 0, "Forward Through Completed": 0, ... etc.
            // Example (Goalkeeping): "Shots Against": 2, "Save Success Rate(%)": 10, "Saves": 0, "Punch Saves": 0 ... etc.
            // Extract all stats listed here accurately. Convert numeric values correctly.
            }
    },
    "selected_team_detailed_stats": { // Data from the right panel, corresponds to selected team in top right.
                                        // This is only applicable if detailed_stats_category is "Summary".
                                        // Extract the second value for each stat in the right panel.
                                        // Example: "Goals": 5, "Shot Accuracy (%)": 40, ... etc.
        "stats": {
            // Key-value pairs from the right panel stats list (second column values).
            // Extract all stats listed here accurately. Convert numeric values correctly.
            }
    }
}
Ensure all text is accurately transcribed and numbers are correctly identified as integers or floats based on the image.
"""