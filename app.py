import base64
import urllib
import dash
import numpy as np
import pandas as pd
import plotly.express as px
from dash import dcc, html
from dash.dependencies import Input, Output
import os

# Style
title_style = {
    'font-family': 'Arial',
    'font-size': '20px',
}

sub_title_style = {
    'font-family': 'Arial',
    'font-size': '16px',
}

input_style = {
    'font-family': 'Arial',
    'width': '100%',
}

grid_layout = {
    'display': 'grid',
    'grid-template-columns': '1fr 4fr',
    'grid-gap': '20px',
    'align-items': 'center',
}

table_style = {
    'font-family': 'Arial',
    'border-collapse': 'collapse',
    'width': '100%',
}

th_style = {
    'border': '1px solid #dddddd',
    'text-align': 'left',
    'padding': '8px',
    'background-color': '#f2f2f2',
}

td_style = {
    'border': '1px solid #dddddd',
    'text-align': 'left',
    'padding': '8px',
}


# Load data
def load_data(file_path, country):
    try:
        df_country = pd.read_csv(file_path.format(country))
        df_country = df_country.rename(columns={
            'fecha': 'Fecha', 'encuestadora': 'Encuestadora',
            'muestra': 'Muestra', 'party': 'Partido',
            'percentage_points': 'Porcentaje_votos'
        })
        df_country['Pais'] = country.capitalize()
        df_country['Fecha'] = pd.to_datetime(df_country['Fecha'])
        return df_country

    except FileNotFoundError:
        print(f"The file '{file_path.format(country)}' does not exist.")
        return None


# Read data
data_path_partido = os.path.join(os.path.dirname(__file__), 'data', 'encuestas_por_partido_{}_2023.csv')
data_path_candidato = os.path.join(os.path.dirname(__file__), 'data', 'encuestas_por_candidato_{}_2023.csv')
countries = ['argentina', 'ecuador', 'guatemala']

polls_all_countries_partido = pd.concat(
    [load_data(data_path_partido, country) for country in countries], ignore_index=True)
polls_all_countries_candidato = pd.concat(
    [load_data(data_path_candidato, country) for country in countries], ignore_index=True)

# App
app = dash.Dash(__name__)
server = app.server

# App layout
app.layout = html.Div([
    html.H1("Agregador de encuestas electorales", style=title_style),
    html.Div([
        html.H1("Seleccione un país", style=sub_title_style),
        dcc.Dropdown(
            id='country-dropdown',
            options=[{'label': pais, 'value': pais} for pais in polls_all_countries_partido['Pais'].unique()],
            value=polls_all_countries_partido['Pais'].unique()[0],
            style=input_style,
        ),
    ], style=grid_layout),
    html.Div([
        html.H1("Seleccione una categoria", style=sub_title_style),
        dcc.Dropdown(
            id='category-dropdown',
            options=[
                {'label': 'Partido', 'value': 'Partido'},
                {'label': 'Candidato', 'value': 'Candidato'}
            ],
            value='Partido',
            style=input_style,
        ),
    ], style=grid_layout),
    html.Div([
        html.H1("Seleccione un periodo", style=sub_title_style),
        dcc.DatePickerRange(
            id='date-range-picker',
            start_date=polls_all_countries_partido['Fecha'].min(),
            end_date=polls_all_countries_partido['Fecha'].max(),
            display_format='YYYY-MM-DD',
            style=input_style,
        )
    ], style=grid_layout),
    html.Div([
        dcc.Graph(id='poll-graph', style={'height': 600}),
        html.A(
            html.Button("Descargar Gráfico", style={
                'background-color': 'orange',
                'color': 'white',
                'padding': '10px 20px',
                'font-size': '16px',
                'border': 'none',
                'border-radius': '5px',
                'cursor': 'pointer',
                'box-shadow': '0 2px 4px rgba(0, 0, 0, 0.2)',
                'transition': 'background-color 0.3s ease',
            }),
            id='download-graph-button',
            download="grafico.png",
            href="",
            target="_blank"
        ),
    ], style={'margin-bottom': '20px'}),
    html.Div([
        html.Table(id='data-table', style=table_style),
        # Add a separate div for space between table and button
        html.Div(style={'margin-bottom': '20px'}),
        html.A(
            html.Button("Descargar Tabla", style={
                'background-color': 'orange',
                'color': 'white',
                'padding': '10px 20px',
                'font-size': '16px',
                'border': 'none',
                'border-radius': '5px',
                'cursor': 'pointer',
                'box-shadow': '0 2px 4px rgba(0, 0, 0, 0.2)',
                'transition': 'background-color 0.3s ease',
            }),
            id='download-table-button',
            download="tabla.csv",
            href="",
            target="_blank"
        )
    ], style={'margin-bottom': '20px'})
])


@app.callback(
    [
        Output('poll-graph', 'figure'),
        Output('data-table', 'children'),
        Output('download-graph-button', 'href'),
        Output('download-table-button', 'href')
    ],
    [Input('country-dropdown', 'value'),
    Input('category-dropdown', 'value'),
     Input('date-range-picker', 'start_date'),
     Input('date-range-picker', 'end_date')]
)
def update_app(selected_country, selected_category, start_date, end_date):
    # Filter the data based on the selected country, category and date range
    if selected_category == 'Partido':
        datos_pais = polls_all_countries_partido[(polls_all_countries_partido['Pais'] == selected_country) &
                                         (polls_all_countries_partido['Fecha'] >= start_date) &
                                         (polls_all_countries_partido['Fecha'] <= end_date)]
    else:
        datos_pais = polls_all_countries_candidato[(polls_all_countries_candidato['Pais'] == selected_country) &
                                         (polls_all_countries_candidato['Fecha'] >= start_date) &
                                         (polls_all_countries_candidato['Fecha'] <= end_date)]

    # Create a set of unique political parties
    parties = set(datos_pais['Partido'].unique())

    # Calculate the trend line for each party
    trend_lines = {}
    for party in parties:
        datos_partido = datos_pais[datos_pais['Partido'] == party]
        coefficients = np.polyfit(datos_partido['Fecha'].astype(np.int64), datos_partido['Porcentaje_votos'], 1)
        trend_lines[party] = np.polyval(coefficients, datos_partido['Fecha'].astype(np.int64))

    figura = px.scatter(datos_pais, x='Fecha', y='Porcentaje_votos',
                        color='Partido',
                        labels={'Partido': 'Partido Político', 'Porcentaje_votos': 'Porcentaje de votos'}
                        if selected_category == 'Partido'
                        else {'Partido': 'Candidato', 'Porcentaje_votos': 'Porcentaje de votos'},
                        title=f'Resultados electorales en {selected_country}', opacity=0.5,
                        trendline='lowess',
                        color_discrete_map={partido: color for partido, color in
                                            zip(datos_pais['Partido'].unique(), px.colors.qualitative.Plotly)},
                        )

    figura.update_layout(showlegend=True)

    # Create the data table
    # Create the table header dynamically with party names
    table_header = [html.Th('Fecha', style=th_style), html.Th('Encuestadora', style=th_style)]
    for party in parties:
        table_header.append(html.Th(party, style=th_style))

    # Create the data table rows
    table_rows = [html.Tr(table_header)]

    # Convert the 'Fecha' column to date objects
    datos_pais['Fecha'] = pd.to_datetime(datos_pais['Fecha'])
    datos_pais['Fecha'] = datos_pais['Fecha'].dt.date

    # Variables to track the last seen date and polling agency
    last_date = None
    last_encuestadora = None

    # Iterate through each row and fill data for each party in the corresponding column
    for _, row in datos_pais.iterrows():
        # Check if the date and polling agency have changed
        if row['Fecha'] != last_date or row['Encuestadora'] != last_encuestadora:
            table_row = [
                html.Td(row['Fecha'], style=td_style),
                html.Td(row['Encuestadora'], style=td_style),
            ]

            # Fill data for each party
            for party in parties:
                party_data = datos_pais[(datos_pais['Partido'] == party) & (datos_pais['Fecha'] == row['Fecha'])]
                if not party_data.empty:
                    party_percentage = party_data.iloc[0]['Porcentaje_votos']
                    if pd.isna(party_percentage):
                        table_row.append(html.Td("", style=td_style))
                    else:
                        table_row.append(html.Td(f"{party_percentage}%", style=td_style))
                else:
                    table_row.append(html.Td("", style=td_style))

            table_rows.append(html.Tr(table_row))

        # Update the last seen date and polling agency
        last_date = row['Fecha']
        last_encuestadora = row['Encuestadora']

    # Generar imagen del gráfico y tabla en formato PNG y CSV respectivamente
    fig = figura
    graph_image = figura.to_image(format="png")
    data_table_df = pd.DataFrame(datos_pais.drop('Pais', axis=1))
    table_csv = data_table_df.to_csv(index=False)

    # Codificar los datos de la imagen y el archivo CSV en base64
    encoded_image = base64.b64encode(graph_image).decode('utf-8')
    encoded_csv = "data:text/csv;charset=utf-8," + urllib.parse.quote(table_csv)

    return figura, table_rows, "data:image/png;base64, " + encoded_image, encoded_csv


# Ejecutar la aplicación
if __name__ == '__main__':
    app.run_server(debug=True)
