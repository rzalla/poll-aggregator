import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import numpy as np


# Function to fetch data from Wikipedia and convert Spanish month names to English
def collect_data_argentina(wikipedia_url_argentina):
    response = requests.get(wikipedia_url_argentina)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all tables in the Wikipedia page
    tables = soup.find_all('table', class_='wikitable')

    def spanish_to_english_month(spanish_month):
        month_map = {
            "enero": "January", "febrero": "February", "marzo": "March",
            "abril": "April", "mayo": "May", "junio": "June",
            "julio": "July", "agosto": "August", "septiembre": "September",
            "octubre": "October", "noviembre": "November", "diciembre": "December"
        }
        return month_map.get(str(spanish_month).lower(), spanish_month)

    def extract_and_parse_date(date_text):
        def replace_month(match):
            spanish_month = match.group(0).split(" ")[-1]
            english_month = spanish_to_english_month(spanish_month)
            return match.group(0).replace(spanish_month, english_month)

        if isinstance(date_text, pd.Series):
            parsed_dates = date_text.str.extract(r"(\d+\s+de\s+\w+\s+de\s+\d{4})", expand=False)
            parsed_dates = parsed_dates.apply(lambda x: re.sub(r"\b\w+\b", replace_month, str(x)))
            parsed_dates = pd.to_datetime(parsed_dates, format="%d de %B de %Y", errors='coerce')
            parsed_date = parsed_dates.dt.strftime("%d/%m/%Y")
        else:
            date_text = str(date_text).strip()
            if date_text:
                parsed_date = re.search(r"(\d+\s+de\s+\w+\s+de\s+\d{4})", date_text)
                if parsed_date:
                    parsed_date = parsed_date.group()
                    parsed_date = re.sub(r"\b\w+\b", replace_month, parsed_date)
                    parsed_dates = pd.to_datetime(parsed_date, format="%d de %B de %Y", errors='coerce')
                    parsed_date = parsed_dates.strftime("%d/%m/%Y")
            else:
                parsed_date = None

        return parsed_date

    # First dataframe: primera
    primera = pd.read_html(str(tables[0]))[0]
    primera = primera.iloc[5:]  # Remove the first row (repeated column names)
    primera = primera.drop(primera.columns[-2:], axis=1) # Remove last two cols
    primera.columns = ["fecha", "encuestadora", "muestra", "fdt", "jxc", "lla", "cf", "fit", "otros", "blanco",
                       "indecisos", "ventaja"]

    # Second dataframe: segunda
    segunda = pd.read_html(str(tables[1]))[0]
    segunda = segunda.iloc[1:]  # Remove the first row (repeated column names)
    segunda.columns = ["fecha", "encuestadora", "muestra", "fdt", "jxc", "lla", "fit", "otros", "blanco", "indecisos",
                       "ventaja"]

    # Third dataframe: ultima
    ultima = pd.read_html(str(tables[2]))[0]
    ultima = ultima.iloc[1:]  # Remove the first row (repeated column names)
    ultima = ultima.drop(ultima.index[3:6])
    ultima.columns = ["fecha", "encuestadora", "muestra", "fdt", "jxc", "lla", "fit", "otros", "blanco", "indecisos",
                      "ventaja"]

    # Combine dataframes
    encuestas = pd.concat([primera, segunda, ultima], ignore_index=True)

    # Format columns
    encuestas["fecha"] = encuestas["fecha"].apply(extract_and_parse_date)
    encuestas['encuestadora'] = encuestas['encuestadora'].str.replace(r'\[\d+\]\u200b', '', regex=True).str.strip()
    cols_to_convert = ["fdt", "jxc", "lla", "cf", "fit", "otros", "blanco", "indecisos", "ventaja", "muestra"]
    encuestas[cols_to_convert] = encuestas[cols_to_convert].apply(pd.to_numeric, errors="coerce")
    encuestas[cols_to_convert[1:]] = encuestas[cols_to_convert[1:]].replace("-", float("nan"))

    # Calculate new column "obi" and drop unnecessary columns
    encuestas["obi"] = encuestas["otros"] + encuestas["blanco"] + encuestas["indecisos"]
    encuestas = encuestas.drop(columns=["otros", "blanco", "indecisos", "ventaja"])

    # Convert to long format
    encuestas_long = encuestas.melt(id_vars=["fecha", "encuestadora", "muestra"], var_name="party",
                                    value_name="percentage_points")
    encuestas_long["party"] = encuestas_long["party"].replace({
        "fdt": "Unión por la Patria", "jxc": "Juntos por el Cambio", "lla": "La Libertad Avanza",
        "cf": "Hacemos por Nuestro Pais", "fit": "Frente de Izquierda", "obi": "Otros - Blanco - Indecisos"
    })
    encuestas_long["percentage_points"] = pd.to_numeric(encuestas_long["percentage_points"], errors="coerce")

    # Fourth dataframe: tercera
    tercera = pd.read_html(str(tables[3]))[0]
    tercera.columns = ["fecha", "encuestadora", "muestra", "massa", "grabois", "bullrich", "larreta", "milei",
                       "bregman", "solano", "schiaretti", "moreno", "otros", "blanco", "indecisos"]
    tercera["fecha"] = tercera["fecha"].apply(extract_and_parse_date)
    cols_to_convert = ["muestra", "massa", "grabois", "bullrich", "larreta", "milei",
                       "bregman", "solano", "schiaretti", "moreno", "otros", "blanco", "indecisos"]
    tercera[cols_to_convert] = tercera[cols_to_convert].replace("-", np.nan)
    tercera[cols_to_convert] = tercera[cols_to_convert].apply(pd.to_numeric, errors="coerce")
    tercera = tercera[["fecha", "encuestadora", "massa", "grabois", "larreta", "bullrich"]].dropna()

    # Convert to long format and update party names
    tercera_long = tercera.melt(id_vars=["fecha", "encuestadora"], var_name="party", value_name="percentage_points")
    tercera_long["party"] = tercera_long["party"].replace({
        "massa": "Sergio Massa", "grabois": "Juan Grabois", "larreta": "Horacio Rodríguez Larreta",
        "bullrich": "Patricia Bullrich"
    })
    tercera_long["coalition"] = tercera_long["party"].replace({
        "Sergio Massa": "Unión por la Patria", "Juan Grabois": "Unión por la Patria",
        "Horacio Rodríguez Larreta": "Juntos por el Cambio", "Patricia Bullrich": "Juntos por el Cambio"
    })
    tercera_long = tercera_long.drop(columns=["party"])

    # Final result
    encuestas_final = pd.concat([encuestas_long, tercera_long], ignore_index=True)

    return encuestas_long, tercera_long

# Collect and save data
wikipedia_url_argentina = "https://es.wikipedia.org/wiki/Anexo:Encuestas_de_intenci%C3%B3n_de_voto_para_las_elecciones_presidenciales_de_Argentina_de_2023"
partido, candidato = collect_data_argentina(wikipedia_url_argentina)
partido.to_csv('../data/encuestas_por_partido_argentina_2023.csv')
candidato.to_csv('../data/encuestas_por_partido_argentina_2023.csv')