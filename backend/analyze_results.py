import pandas as pd
import json


# Funktion zum Einlesen der Daten
def load_data(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    return pd.DataFrame(data)


# Funktion zur Analyse der besten Kombinationen
def analyze_best_combinations(df):
    # Gruppiere die Daten nach QAM-Symbolrate und Frequenztrennung und berechne die durchschnittliche BER
    best_combinations = (
        df.groupby(["qam_symbol_rate", "freq_separation"])["ber"].mean().reset_index()
    )

    # Finde die Kombination mit der niedrigsten durchschnittlichen BER
    best_result = best_combinations.loc[best_combinations["ber"].idxmin()]

    return best_result


# Hauptfunktion
def main():
    # Pfad zur Datendatei (bitte anpassen)
    file_path = "/Users/mba/Desktop/batch_optimization_results.txt"

    # Daten einlesen
    df = load_data(file_path)

    # Analyse durchführen
    best_result = analyze_best_combinations(df)

    # Ergebnisse ausgeben
    print("Beste Kombination über alle SNRs hinweg:")
    print(
        f"QAM-Symbolrate: {best_result['qam_symbol_rate']}, Frequenztrennung: {best_result['freq_separation']}, Durchschnittliche BER: {best_result['ber']}"
    )


# Ausführung der Hauptfunktion
if __name__ == "__main__":
    main()
