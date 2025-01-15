
import gradio as gr
import numpy as np
import pandas as pd
from gradio_folium import Folium
from smolagents.gradio_ui import pull_messages_from_step
from smolagents.types import handle_agent_output_types, AgentText
from folium import Map, TileLayer, Marker, Icon, Popup
from folium.plugins import Fullscreen

FINAL_MESSAGE_HEADER = "**Final answer/ Réponse finale** \n 🤖⛷️💭"

MAP_URL = "https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png"

def toggle_visibility(show):
    return gr.Textbox(visible=show)

def create_map_from_markers(dataframe: pd.DataFrame) -> Map:
    """
    Create a  Folium map with markers for each location in the dataframe.
    Args:
        dataframe (pd.DataFrame): Dataframe containing the locations.
    
    Returns:
        Map: Folium map with markers.
    """
   
    f_map = Map(
        location=[dataframe["Latitude"].mean(), dataframe["Longitude"].mean()],
        zoom_start=10,
        tiles=
        TileLayer(
            tiles=MAP_URL,
            attr="Google",
            name="Google Maps",
            overlay=True,
            control=True,
        ),
    )
    for _, row in dataframe.iterrows():
        if np.isnan(row["Latitude"]) or np.isnan(row["Longitude"]):
            continue
        #popup_message = f"<h4 style='color: #d53e2a;'>{row['name'].split(',')[0]}</h4><p style='font-weight:500'>{row['description']}</p>"
        #popup_message += f"<a href='https://www.google.com/search?q={row['name']}' target='_blank'><b>Learn more about {row['name'].split(',')[0]}</b></a>"

        marker = Marker(
            location=[float(row["Latitude"]), float(row["Longitude"])],
            icon=Icon(color="blue", icon="fa-map-marker", prefix='fa'),
            popup = Popup(f"Infos: <a href='{row['Route Link']}'>{row['Name']}</a>", max_width=300)
        )
        marker.add_to(f_map)
    
    Fullscreen(position='topright', title='Expand me', title_cancel='Exit me', force_separate_button=True).add_to(f_map)

    bounds = [[float(row["Latitude"]), float(row["Longitude"])] for _, row in dataframe.iterrows()]
    f_map.fit_bounds(bounds, padding=(100, 100))
    return f_map


def update_map_on_selection(row: pd.Series, df_routes: gr.State) -> Map:
    """
    Update the map with a marker at the selected location.
    Args:
        row (pd.Series): Selected row from the dataframe.
    Returns:
        Map: Updated Folium map.
    """
    row  = df_routes.loc[df_routes['Name'] == row['Name']]

    f_map = Map(
        location=[row["Latitude"][0], row["Longitude"][0]],
        zoom_start=10,
        tiles=TileLayer(
            tiles=MAP_URL,
            attr="Google",
            name="Google Maps",
            overlay=True,
            control=True,
        ),
    )
    popup = Popup(f"Infos: <a href='{row['Route Link'][0]}'>{row['Name'][0]}</a>", max_width=300)
    Marker(
        location=[row["Latitude"][0], row["Longitude"][0]],
        icon=Icon(color="blue", icon="fa-map-marker", prefix='fa'),
        popup=popup
    ).add_to(f_map)

    Fullscreen(position='topright', title='Expand', title_cancel='Exit', force_separate_button=True).add_to(f_map)

    return f_map


# Simplified interaction function
def interact_with_agent(agent, prompt, messages, df_routes, additional_args):
    
    messages.append(gr.ChatMessage(role="user", content=prompt))
    yield (messages, df_routes, gr.Textbox(value=FINAL_MESSAGE_HEADER, container=True))

    for msg, _df_routes, final_message in stream_to_gradio(
        agent,
        df_routes=df_routes,
        task=prompt,
        reset_agent_memory=True,
        additional_args=additional_args,
    ):
        messages.append(msg)
        yield (messages, _df_routes, final_message)

    yield (messages, _df_routes, final_message)
    
    
def stream_to_gradio(
    agent,
    df_routes,
    task: str,
    test_mode: bool = False,
    reset_agent_memory: bool = False,
    **kwargs,
):
    """Runs an agent with the given task and streams the messages from the agent as gradio ChatMessages."""

    for step_log in agent.run(task, stream=True, reset=reset_agent_memory, **kwargs):
        for message in pull_messages_from_step(step_log, test_mode=test_mode):
            yield (message, df_routes,  gr.Markdown(value=FINAL_MESSAGE_HEADER , container=True))

    final_answer = step_log  # Last log is the run's final_answer
    final_answer = handle_agent_output_types(final_answer)
    if isinstance(final_answer, dict):
        final_message = final_answer.get("message")
        itineraries = final_answer.get("itineraries")
        if itineraries:
            print("HEEERE")
            df_routes = pd.DataFrame(itineraries)
            df_routes.columns = ["id", "Name", "Latitude", "Longitude", "Route Link"]
            print(df_routes)
            
    else:
        final_message = final_answer
        
    text_output = gr.Markdown(value=FINAL_MESSAGE_HEADER + f": {str(final_message)}", container=True)
    if isinstance(final_answer, AgentText):
        yield (gr.ChatMessage(
            role="assistant",
            content=f"**Final answer:**\n{str(final_message)}\n",
        ), df_routes, text_output) 

    else:
        yield (gr.ChatMessage(role="assistant", content=str(final_message)), df_routes, text_output)
