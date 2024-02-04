import gradio as gr
import argparse

from openai import OpenAI
from icalendar import Calendar, Event, vCalAddress, vText
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date
from dateutil.parser import ParserError
import pytz
import json
import os

# Initialize the OpenAI client with your local server details
client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")

# Directory for storing event descriptions temporarily
event_directory = "event_descriptions"
if not os.path.exists(event_directory):
    os.makedirs(event_directory)


def generate_json_for_event(event_description):
    completion = client.chat.completions.create(
        model="local-model",  # This field is a placeholder
        messages=[
    {
        "role": "system",
        "content": "Given a detailed or partial description of an event, output a structured JSON representation of the event. The JSON should remain flat (TOP-LEVEL ONLY) and focus on including the following fields where applicable: 'summary', 'description', 'start', 'end', 'location', 'organizer', and 'attendees'. Avoid creating additional fields or subfields. When specific details like 'end' time, 'organizer' details, or 'location' are not provided, leave those fields blank or omit them if inapplicable. Strive for accuracy with the provided details, and use inference judiciously to fill in gaps without introducing unwarranted assumptions. This task emphasizes adaptability to both comprehensive and limited inputs, reflecting a more dynamic approach to information parsing and structuring. NEVER EVER write notes or explanations!"
    },
    {
        "role": "user",
        "content": "Event: Annual Marketing Strategy Meeting. Description: Focus on digital transformation and innovation within marketing efforts, with keynote speakers from top tech companies, workshops, and a networking lunch. Date: March 15th, 2024. Start Time: 10:00 AM. End Time: 3:00 PM. Location: Downtown Conference Center, Room A1."
    },
    {
        "role": "assistant",
        "content": "{\"summary\": \"Annual Marketing Strategy Meeting\", \"description\": \"Focus on digital transformation and innovation within marketing efforts, with keynote speakers from top tech companies, workshops, and a networking lunch.\", \"start\": \"2024-03-15T10:00:00\", \"end\": \"2024-03-15T15:00:00\", \"location\": \"Downtown Conference Center, Room A1\"}"
    },
    {
    "role": "user",
    "content": "ud med hunden, 5.2.2024 kl7; tager 1.5 timer;"
    },
    {
        "role": "assistant",
        "content": "{\"summary\": \"Walking the dog\", \"description\": \"\", \"start\": \"2024-02-05T07:00:00\", \"end\": \"2024-02-05T08:30:00\", \"location\": \"\", \"organizer\": \"\", \"attendees\": \"\"}"
    },
    {
        "role": "user", 
        'content': event_description
    }
        ],
        temperature=0.3,
    )
    json_output = completion.choices[0].message
    return json_output

def create_event_from_json(event_json):
    event_data = extract_json_from_mixed_input(event_json)
    event = Event()

    # Summary
    event.add('summary', event_data.get('summary', 'No Title Provided'))

    # Start and End time with dateutil's parse
    for time_field in ['start', 'end']:
        time_str = event_data.get(time_field)
        if time_str:
            try:
                parsed_time = parse_date(time_str)
                event.add(f'dt{time_field}', parsed_time)
            except ParserError:
                pass  # If parsing fails, simply skip this field

    # Description
    event.add('description', event_data.get('description', 'No Description Provided'))

    # Location
    event.add('location', event_data.get('location', 'Location Not Specified'))

    # Organizer and Attendees
    if 'organizer' in event_data:
        event.add('organizer', event_data['organizer'])
    if 'attendees' in event_data:
        event.add('attendees', event_data['attendees'])

    return event

def extract_json_from_mixed_input(input_str):
    """
    Extracts the JSON part from a mixed string that may contain additional text outside the JSON structure.
    
    Args:
    - input_str (str): The input string potentially containing JSON data mixed with other text.
    
    Returns:
    - dict: The extracted JSON data as a Python dictionary, or None if JSON extraction fails.
    """
    try:
        # Find the first opening brace and the last closing brace to isolate JSON
        start_index = input_str.find('{')
        end_index = input_str.rfind('}') + 1  # Include the closing brace in the slice
        if start_index != -1 and end_index != -1:
            json_str = input_str[start_index:end_index]
            json_data = json.loads(json_str)
            return json_data
        else:
            return None  # No valid JSON structure found
    except json.JSONDecodeError:
        return None  # JSON parsing failed

# Directory for storing event descriptions temporarily
event_directory = "event_descriptions"
if not os.path.exists(event_directory):
    os.makedirs(event_directory)
# Function to add an event description to the directory
def add_event(event_info):
    event_id = len(os.listdir(event_directory)) + 1
    file_path = os.path.join(event_directory, f"event_{event_id}.txt")
    with open(file_path, 'w') as file:
        file.write(event_info)
    return f"Event {event_id} added. Overview updated below.", ""


# Function to create a calendar from event descriptions
def make_calendar():
    cal = Calendar()
    for filename in os.listdir(event_directory):
        file_path = os.path.join(event_directory, filename)
        with open(file_path, 'r') as file:
            event_description = file.read()
        event_json = generate_json_for_event(event_description)

        cal.add_component(create_event_from_json(event_json.content))
    # Save the .ics file
    ics_file_path = "compiled_events.ics"
    with open(ics_file_path, 'wb') as ics_file:
        ics_file.write(cal.to_ical())
    # Clear event directory
    for filename in os.listdir(event_directory):
        os.remove(os.path.join(event_directory, filename))
    return f"Calendar created with {len(cal.subcomponents)} events. Event descriptions cleared.", ""

# Gradio interface setup
def update_overview():
    events = []
    for filename in os.listdir(event_directory):
        with open(os.path.join(event_directory, filename), 'r') as file:
            events.append(file.readline().strip()+'\n')  # Assuming first line is a summary
    return "\n".join(events)

# Initialize the argument parser
parser = argparse.ArgumentParser(description="CLI for managing events and generating calendars.")
# Add an argument for starting the Gradio server
parser.add_argument('--start-server', action='store_true', help="Start the Gradio server.")
parser.add_argument('--port', type=int, default=7860, help="Gradio server port. Default is 7860.")

# Parse the command line arguments
args = parser.parse_args()

# Function to launch the Gradio app
def launch_gradio_app():
    with gr.Blocks() as app:
        with gr.Row():
            event_input = gr.Textbox(label="Paste event info here", lines=10, placeholder="Event details...")
            add_button = gr.Button("Add Event")
        overview = gr.Textbox(label="Events Overview", lines=5, interactive=False)
        make_cal_button = gr.Button("Make Calendar")
        progress = gr.Textbox(label="Progress", interactive=False)

        add_button.click(fn=add_event, inputs=event_input, outputs=[progress, event_input])
        make_cal_button.click(fn=make_calendar, inputs=None, outputs=[progress, overview])
        add_button.click(fn=update_overview, inputs=None, outputs=overview)

    app.launch(server_port=args.port)

# Check if the --start-server flag was provided
if args.start_server:
    launch_gradio_app()
else:
    print("Gradio server not started. Provide --start-server to start.")