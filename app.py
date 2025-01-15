import os
import json
import pandas as pd
import numpy as np
import gradio as gr
from gradio_folium import Folium
from smolagents import CodeAgent, LiteLLMModel, HfApiModel
from src.gradio_utils import ( create_map_from_markers,
                              update_map_on_selection, 
                              stream_to_gradio, 
                              interact_with_agent, 
                              toggle_visibility, 
                              FINAL_MESSAGE_HEADER,
                              MAP_URL)

from src.prompts import SKI_TOURING_ASSISTANT_PROMPT
from src.tools import (RefugeTool,
                       MountainRangesTool,
                      ForecastTool,
                      GetRoutesTool,
                      DescribeRouteTool, 
                      RecentOutingsTool)
from folium import Map, TileLayer, Marker, Icon
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


required_variables = [
    "HF_TOKEN", 
    "GOOGLE_MAPS_API_KEY", 
    "SKITOUR_API_TOKEN", 
    "METEO_FRANCE_API_TOKEN",
    "HUGGINGFACE_ENDPOINT_ID_QWEN"
    ]

# Find missing variables
missing_variables = [var for var in required_variables if var not in os.environ]

if missing_variables:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_variables)}")

print("All required variables are set.")

# Load the summit clusters
# Useful for assigning locations to mountain ranges
with open("data/summit_clusters.json", "r") as f:
    summit_clusters = json.load(f)
    
with open("data/skitour2mf_lookup.json", "r") as f:
    skitour2mf_lookup = json.load(f)

def get_tools(llm_engine):
    mountain_ranges_tool = MountainRangesTool(summit_clusters)
    forecast_tool = ForecastTool(
        llm_engine=llm_engine, 
        clusters=summit_clusters, 
        skitour2meteofrance=skitour2mf_lookup
        )
    get_routes_tool = GetRoutesTool()
    description_route_tool = DescribeRouteTool(
        skitour2meteofrance=skitour2mf_lookup, 
        llm_engine=llm_engine
        )
    recent_outings_tool = RecentOutingsTool()
    return [mountain_ranges_tool, forecast_tool, get_routes_tool, description_route_tool, recent_outings_tool]

# Initialize the default agent
def init_default_agent(llm_engine):
    return CodeAgent(
            tools = get_tools(llm_engine),
            model = llm_engine,
            additional_authorized_imports=["pandas"],
            max_steps=10,
    )
    
# Initialize the default agent prompt
def init_default_agent_prompt():
    return {"specific_agent_role_prompt": SKI_TOURING_ASSISTANT_PROMPT.format(language="French")}

def create_llm_engine(type_engine: str, api_key: str = None):
    if type_engine == "openai/gpt-4o" and api_key:
        llm_engine = LiteLLMModel(model_id="openai/gpt-4o", api_key=api_key)
        return llm_engine
    elif type_engine == "openai/gpt-4o" and not api_key:
        raise ValueError("You need to provide an API key to use the the model engine.")
    elif type_engine == "Qwen/Qwen2.5-Coder-32B-Instruct":
        llm_engine = HfApiModel(model_id=os.environ["HUGGINGFACE_ENDPOINT_ID_QWEN"])
        return llm_engine
    elif type_engine == "meta-llama/Llama-3.3-70B-Instruct":
        llm_engine = HfApiModel(model_id=os.environ["HUGGINGFACE_ENDPOINT_ID_LLAMA"])
        return llm_engine
    else:
        raise ValueError("Invalid engine type. Please choose either 'openai/gpt-4o' or 'Qwen/Qwen2.5-Coder-32B-Instruct'.")
    
def initialize_new_agent(engine_type, api_key):
    try:
        llm_engine = create_llm_engine(engine_type, api_key)
        tools = get_tools(llm_engine)
        skier_agent =  CodeAgent(
            tools = tools,
            model = llm_engine,
            additional_authorized_imports=["pandas"],
            max_steps=10,
    )
        return skier_agent, [], gr.Chatbot([], label="Agent Thoughts", type="messages")
    except ValueError as e:
        return str(e)
    
# Sample data for demonstration
sample_data = {
    "id": [0],
    "Name": "Mont Blanc, Par les Grands Mulets",
    "Latitude": [45.90181],
    "Longitude": [6.86153],
    "Route Link": ["https://skitour.fr/topos/770"],
}
df_sample_routes = pd.DataFrame(sample_data)

# Default engine
if os.environ.get("OPENAI_API_KEY"):
    default_engine = create_llm_engine("openai/gpt-4o", os.environ.get("OPENAI_API_KEY"))
else:
    default_engine = create_llm_engine("Qwen/Qwen2.5-Coder-32B-Instruct")


# Gradio UI
def build_ui():
    
    custom_css = """
    .custom-textbox {
        border: 2px solid #1E90FF; /* DodgerBlue border */
        border-radius: 10px;
        padding: 10px;
        background-color: #b4e2f0; /* Light blue background */
        font-size: 16px; /* Larger font size */
        color: #1E90FF; /* Blue text color */
    }
"""  

    with gr.Blocks(
        theme=gr.themes.Soft(
            primary_hue=gr.themes.colors.blue,
            secondary_hue=gr.themes.colors.blue), css=custom_css
        ) as demo:
        gr.Markdown("<center><h1>Alpine Agent</h1></center>", )
        gr.Markdown("<center>Plan your next ski touring trip with AI agents!</center>", )
        
        gr.Image(value="./data/skitourai.jpeg", height=300, width=300)
        with gr.Accordion("About the App❓", open=False):
            gr.Markdown("""
 **🇬🇧 English Version**

The Ski Touring Assistant is built with the **[Smolagents](https://github.com/huggingface/smolagents) library by Hugging Face** and relies on data from [Skitour.fr](https://skitour.fr) and [Météo France - Montagne](https://meteofrance.com/meteo-montagne). 
It is designed specifically to help plan ski touring routes **in the Alps and the Pyrenees, in France only**. While the app provides AI-generated suggestions, it is essential to **always verify snow and avalanche conditions directly on Météo-France for your safety.**

#### Key Features

- **Interactive Maps**: Plan routes with data from [Skitour.fr](https://skitour.fr), covering ski touring trails in the Alps and the Pyrenees.  
- **AI Assistance**: Get route recommendations, hazard insights, and metrics like elevation and travel time.  
- **Snow & Avalanche Conditions**: Access real-time information via [Météo-France](https://meteofrance.com/meteo-montagne).  
- **Multilingual Support**: Available in English and French.

Enjoy your ski touring adventures in France, but always double-check official sources for safety!

---
**🇫🇷 Version Française**

L'assistant de ski de randonnée est construit avec la bibliothèque **[Smolagents](https://github.com/huggingface/smolagents) de Hugging Face** et repose sur les données de [Skitour.fr](https://skitour.fr) et [Météo France - Montagne](https://meteofrance.com/meteo-montagne). 
Il est conçu spécifiquement pour aider à planifier des itinéraires de ski de randonnée **dans les Alpes et les Pyrénées, uniquement en France**. Bien que l'application fournisse des suggestions générées par IA, il est essentiel de **toujours vérifier la météo et le bulletin d'estimation des risques d'avalanche (BERA) directement sur Météo-France pour votre sécurité**.

#### Principales Fonctionnalités

- **Cartes interactives** : Planifiez des itinéraires avec des données de [Skitour.fr](https://skitour.fr), couvrant les sentiers de ski de randonnée dans les Alpes et les Pyrénées.  
- **Assistance IA** : Obtenez des recommandations d'itinéraires, des informations sur les risques et des métriques comme l'altitude et le temps de trajet.  
- **Conditions de neige et d'avalanche** : Accédez à des informations en temps réel via [Météo-France](https://meteofrance.com/meteo-montagne).  
- **Support multilingue** : Disponible en anglais et en français.

Profitez de vos aventures en ski de randonnée en France, mais vérifiez toujours les sources officielles pour votre sécurité !
""", container=True)
        

        
        skier_agent = gr.State(lambda: init_default_agent(default_engine))
        with gr.Row():
            with gr.Column():
                language = gr.Radio(["English", "French"], value="French", label="Language")
                skier_agent_prompt = gr.State(init_default_agent_prompt)
                language_button = gr.Button("Update language")
                model_type = gr.Dropdown(choices = ["Qwen/Qwen2.5-Coder-32B-Instruct", "meta-llama/Llama-3.3-70B-Instruct", "openai/gpt-4o", ], 
                                         value="Qwen/Qwen2.5-Coder-32B-Instruct",
                                         label="Model Type", 
                                         info="If you choose openai/gpt-4o, you need to provide an API key.", 
                                         interactive=True
                                         )
                api_key_textbox = gr.Textbox(label="API Key", placeholder="Enter your API key", type="password", visible=False)
              
        
                model_type.change(
                    lambda x: toggle_visibility(True) if x =='openai/gpt-4o' else toggle_visibility(False), 
                    [model_type], 
                    [api_key_textbox]
                    )
                update_engine = gr.Button("Update LLM Engine")
                
              
                stored_message = gr.State([])
                chatbot = gr.Chatbot(label="Agent Thoughts", type="messages")
                warning = gr.Warning("The agent can take few seconds to minutes to respond.", visible=True)
                text_output = gr.Markdown(value=FINAL_MESSAGE_HEADER, container=True)
                warning = gr.Markdown("⚠️ The agent can take few seconds to minutes to respond.", container=True)
                text_input = gr.Textbox(lines=1, label="Chat Message", submit_btn=True, elem_classes=["custom-textbox"])
                with gr.Accordion("🇬🇧 English examples"):
                    gr.Examples(["Can you suggest a ski touring itinerary, near Chamonix, of moderate difficulty, with good weather and safe avalanche conditions? ", 
                                 "What are current weather and avalanche conditions in the Vanoise range?"], text_input)
                with gr.Accordion("🇫🇷 Exemples en français", open=False):
                    gr.Examples(["Poux-tu suggérer un itinéraire de ski de randonnée, près de Chamonix, d'une difficulté modérée, avec de bonnes conditions météorologiques et un risque avalanche peu élevé?", 
                                 "Quelles sont les conditions météorologiques et le risque avalanche dans le massif de la Vanoise ?"], text_input)
       
            with gr.Column():
                f_map = Folium(value=Map(
                    location=[45.9237, 6.8694],
                    zoom_start=10,
                    tiles= TileLayer(
                                tiles=MAP_URL,
                                attr="Google",
                                name="Google Maps",
                                overlay=True,
                                control=True )
                            )
                )
                               
                df_routes = gr.State(pd.DataFrame(df_sample_routes))
                data = gr.DataFrame(value=df_routes.value[["Name", "Route Link"]], datatype="markdown", interactive=False)
        
                language_button.click(lambda s: {"specific_agent_role_prompt": SKI_TOURING_ASSISTANT_PROMPT.format(language=s)}, [language], [skier_agent_prompt])
                update_engine.click(
                    fn=initialize_new_agent,
                    inputs=[model_type, api_key_textbox],
                    outputs=[skier_agent, stored_message, chatbot]
                    )

                text_input.submit(lambda s: (s, ""), [text_input], [stored_message, text_input]) \
                    .then(interact_with_agent, [skier_agent, stored_message, chatbot, df_routes, skier_agent_prompt], [chatbot, df_routes, text_output])

                df_routes.change(create_map_from_markers, [df_routes], [f_map]).then(lambda s: gr.DataFrame(s[["Name", "Route Link"]], datatype="markdown", interactive=False), [df_routes], [data])
                data.select(
                    update_map_on_selection, [data, df_routes],[f_map]
                )

    demo.launch()

# Launch the app
if __name__ == "__main__":
    build_ui()
