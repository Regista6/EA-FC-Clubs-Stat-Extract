import warnings

warnings.filterwarnings("ignore", category=UserWarning)

from google import genai
import os
import sys
import json
from PIL import Image
import pandas as pd
import time
from glob import glob
import shutil
import input


def merge_stat_files(folder_path, file_prefix, output_file):
    """
    Args:
        folder_path (str): Folder containing temporary Excel files.
        file_prefix (str): Prefix of the Excel filenames.
        output_file (str): Output Excel file path.
    """
    all_files = glob(os.path.join(folder_path, f"{file_prefix}*.xlsx"))
    if not all_files:
        print("No files found with given prefix.")
        return

    # Use the first file to get sheet names and read first two sheets
    first_file = all_files[0]
    xl = pd.ExcelFile(first_file)

    if len(xl.sheet_names) < 3:
        print("First file does not contain at least 3 sheets.")
        return

    sheet_name_1 = xl.sheet_names[0]
    sheet_name_2 = xl.sheet_names[1]
    sheet_name_3 = xl.sheet_names[2]

    sheet1 = xl.parse(sheet_name_1)
    sheet2 = xl.parse(sheet_name_2)

    if "Summary" in file_prefix:
        sheet_name_4 = xl.sheet_names[3]
        sheet4 = xl.parse(sheet_name_4)

    # Merge the third sheet from all files
    combined_third_sheet = pd.DataFrame()
    for file in all_files:
        try:
            xl_file = pd.ExcelFile(file)
            if len(xl_file.sheet_names) >= 3:
                df = xl_file.parse(xl_file.sheet_names[2])
                combined_third_sheet = pd.concat(
                    [combined_third_sheet, df], ignore_index=True
                )
            else:
                print(f"Skipping {file}: Less than 3 sheets.")
        except Exception as e:
            print(f"Error reading {file}: {e}")

    # Drop duplicates by 'Stat' column
    if "Stat" in combined_third_sheet.columns:
        combined_third_sheet = combined_third_sheet.drop_duplicates(subset="Stat")

    # Save all three sheets to a new Excel file with original names
    with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
        sheet1.to_excel(writer, index=False, sheet_name=sheet_name_1)
        sheet2.to_excel(writer, index=False, sheet_name=sheet_name_2)
        combined_third_sheet.to_excel(writer, index=False, sheet_name=sheet_name_3)
        if "Summary" in file_prefix:
            sheet4.to_excel(writer, index=False, sheet_name=sheet_name_4)

    # Some Post-Processing
    if "Passing" in file_prefix or "Possession" in file_prefix:
        all_sheets = pd.read_excel(output_file, sheet_name=None)
        df_target = all_sheets[sheet_name_3]
        exclude_values = [
            "Around Attempted",
            "Around Completed",
            "Over Attempted",
            "Over Completed",
            "Through Attempted",
            "Through Completed",
        ]
        df_target_filtered = df_target[~df_target["Stat"].isin(exclude_values)]
        all_sheets[sheet_name_3] = df_target_filtered
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            for sheet_name, sheet_df in all_sheets.items():
                sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"✅ Merged Excel saved to: {output_file}")


# --- Function to Save Data to Excel ---
def save_to_excel(data, idx, filename="game_stats.xlsx"):
    """
    Saves the extracted game statistics data to an Excel file with multiple sheets.

    Args:
        data (dict): The dictionary containing the extracted data.
        filename (str): The desired name for the output Excel file.

    Returns:
        bool: True if the file was saved successfully, False otherwise.
    """
    if not isinstance(data, dict):
        print("Error saving to Excel: Input 'data' must be a dictionary.")
        return False

    required_keys = [
        "team_name",
        "featured_player",
        "player_list",
        "detailed_stats_category",
        "selected_player_detailed_stats",
    ]
    if not all(key in data for key in required_keys):
        print(
            f"Error saving to Excel: Input 'data' is missing one or more required keys: {required_keys}"
        )
        return False

    try:
        detailed_stats_category = data.get("detailed_stats_category", "N/A")
        filename = f"Stats_{detailed_stats_category}_{idx}.xlsx"
        print(f"\n--- Attempting to save data to '{filename}' ---")

        with pd.ExcelWriter(
            f"{input.OUTPUT_TEMP_FOLDER}/{filename}", engine="openpyxl"
        ) as writer:
            # Sheet 1: Summary
            summary_data = {
                "Team Name": data.get("team_name", "N/A"),
                "Featured Player Name": data.get("featured_player", {}).get(
                    "name", "N/A"
                ),
                "Featured Player OVR": data.get("featured_player", {}).get(
                    "overall_rating", "N/A"
                ),
                "Featured Player MR": data.get("featured_player", {}).get(
                    "match_rating", "N/A"
                ),
                "Detailed Stats Category": data.get("detailed_stats_category", "N/A"),
            }
            df_summary = pd.Series(summary_data).to_frame(name="Value")
            df_summary.to_excel(writer, sheet_name="Summary", index=True, header=True)

            # Sheet 2: Player List
            player_list = data.get("player_list", [])
            if player_list:
                columns_order = ["position", "name", "match_rating", "goals", "assists"]
                df_players = pd.DataFrame(player_list)
                df_players = df_players.reindex(columns=columns_order, fill_value=0)
                df_players.to_excel(writer, sheet_name="Player List", index=False)
            else:
                print("Warning: Player list is empty. Skipping 'Player List' sheet.")

            # Sheet 3: Detailed Stats for Selected Player
            detailed_stats_info = data.get("selected_player_detailed_stats", {})
            detailed_stats_category = data.get("detailed_stats_category", "N/A")
            featured_player_name = data.get("featured_player", {}).get("name", "N/A")
            stats_dict = detailed_stats_info.get("stats", {})
            if stats_dict:
                df_detailed = pd.DataFrame(
                    list(stats_dict.items()), columns=["Stat", "Value"]
                )
                sheet_name_detailed = (
                    f"{detailed_stats_category}_{featured_player_name}"[:31]
                )  # Limit sheet name length
                df_detailed.to_excel(
                    writer, sheet_name=sheet_name_detailed, index=False
                )
            else:
                print(
                    "Warning: Detailed player stats dictionary is empty. Skipping detailed stats sheet."
                )

            # Sheet 4: Detailed team stats when stat category is Summary
            if detailed_stats_category == "Summary":
                selected_team_info = data.get("selected_team_detailed_stats", {})
                featured_team_name = data.get("team_name", "N/A")
                team_stats_dict = selected_team_info.get("stats", {})
                if team_stats_dict:
                    df_detailed = pd.DataFrame(
                        list(team_stats_dict.items()), columns=["Stat", "Value"]
                    )
                    sheet_name_detailed = (
                        f"{detailed_stats_category}_{featured_team_name}"[:31]
                    )  # Limit sheet name length
                    df_detailed.to_excel(
                        writer, sheet_name=sheet_name_detailed, index=False
                    )
                else:
                    print(
                        "Warning: Detailed team stats dictionary is empty. Skipping detailed stats sheet."
                    )

        print(f"Successfully saved data to '{filename}'")
        return True

    except KeyError as e:
        print(f"Error saving to Excel: Missing expected key in data structure: {e}")
        return False
    except ImportError:
        print(
            "Error saving to Excel: pandas or openpyxl library not found. Please install using 'pip install pandas openpyxl'"
        )
        return False
    except Exception as e:
        print(f"An unexpected error occurred while saving to Excel: {e}")
        return False


def create_fresh_directory(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)


# --- Main Execution ---
if __name__ == "__main__":

    create_fresh_directory(input.OUTPUT_TEMP_FOLDER)
    create_fresh_directory(input.OUTPUT_IMAGE_FOLDER)

    for idx, IMAGE_FILE in enumerate(os.listdir(input.INPUT_IMAGE_FOLDER)):
        if not IMAGE_FILE.endswith(".png"):
            continue
        time.sleep(3)
        # 1. Check and Configure API Key
        if not os.environ.get("GEMINI_API_KEY"):
            print("Error: API Key not found.")
            print(
                "Please set the GOOGLE_API_KEY environment variable or paste the key directly into the script."
            )
            sys.exit(1)

        try:
            gemini_api_key = os.environ.get("GEMINI_API_KEY")
            genai_client = genai.Client(api_key=gemini_api_key)
            print(f"--- Using Model: {input.MODEL_NAME} ---")
        except Exception as e:
            print(f"Error configuring Generative AI SDK or creating model: {e}")
            sys.exit(1)

        # 2. Load Image
        try:
            print(f"\n--- Loading Image: {input.INPUT_IMAGE_FOLDER}/{IMAGE_FILE} ---")
            img = Image.open(f"{input.INPUT_IMAGE_FOLDER}/{IMAGE_FILE}")
        except FileNotFoundError:
            print(
                f"Error: Image file not found at '{input.INPUT_IMAGE_FOLDER}/{IMAGE_FILE}'"
            )
            print(
                "Please make sure the image file exists in the same directory or provide the correct path."
            )
            sys.exit(1)
        except Exception as e:
            print(f"Error loading image: {e}")
            sys.exit(1)

        # 3. Call Gemini API and Process Response
        extracted_data = None
        print("\n--- Sending Prompt and Image to Gemini ---")
        try:
            # Send both the text prompt and the image object
            response = genai_client.models.generate_content(
                model=input.MODEL_NAME, contents=[input.GEMINI_PROMPT, img]
            )

            print("\n--- Gemini Raw Response Text ---")

            print("\n--- Attempting to Parse JSON ---")
            # Clean the response text (remove potential markdown backticks and surrounding whitespace)
            cleaned_text = response.text.strip().strip("```json").strip("```").strip()

            # Parse the cleaned text as JSON
            extracted_data = json.loads(cleaned_text)

            print("\n--- Extracted Data (Parsed JSON) ---")
            # print(json.dumps(extracted_data, indent=2)) # Pretty print

        except json.JSONDecodeError as e:
            print(f"\n--- Error: Failed to parse Gemini response as JSON ---")
            print(f"JSONDecodeError: {e}")
            print(
                "The model might not have returned valid JSON. Check the 'Raw Response Text' above."
            )
            print("You might need to adjust the prompt for stricter JSON output.")
            # Optionally print safety feedback if available
            if hasattr(response, "prompt_feedback") and response.prompt_feedback:
                print("\nPrompt Feedback (Safety Ratings):")
                print(response.prompt_feedback)
            sys.exit(1)  # Exit if parsing fails

        except Exception as e:
            print(f"\n--- An Error Occurred During Generation or Parsing ---")
            print(f"Error: {e}")
            if hasattr(response, "prompt_feedback") and response.prompt_feedback:
                print("\nPrompt Feedback (Safety Ratings):")
                print(response.prompt_feedback)
            sys.exit(1)  # Exit on other generation errors

        # 4. Save to Excel (only if data was successfully extracted and parsed)
        if extracted_data:
            success = save_to_excel(extracted_data, idx)
            if success:
                print(f"\n--- End-to-End Process Complete ---")
                print(response.usage_metadata)
            else:
                print("\n--- Process Completed with Errors During Excel Save ---")
        else:
            print("\n--- Process Halted: Data extraction failed ---")

    # 5. Merge the files
    for file_prefix in input.STAT_CATEGORIES:
        merge_stat_files(
            folder_path=input.OUTPUT_TEMP_FOLDER,
            file_prefix=file_prefix,
            output_file=f"{input.OUTPUT_IMAGE_FOLDER}/{file_prefix}_Final.xlsx",
        )
