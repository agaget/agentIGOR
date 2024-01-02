#!/usr/bin/env python
"""AgentIGOR à l'écoute.

Agent Immobilier, Geolocalisaion, Osint et Recherche.
"""
from __future__ import annotations

import argparse
import logging
import shelve

import requests
from tqdm import tqdm

cacheville = shelve.open("town.cache")  # noqa: S301
cacheparcelle = shelve.open("parcelles.cache")  # noqa: S301

MAX_RETURNED_API_CARTO = 1000
MINIMUM_DATE = 1515


class Parcelle:
    """Classe Parcelle."""

    def __init__(
        self: Parcelle,
        section: str,
        numero: str,
        code_ville: int,
    ) -> None:
        """Constructeur de parcelle."""
        self.section = section
        self.numero = numero
        self.code_ville = code_ville
        self.adresse = ""
        self.annee_construction = 1515
        self.contenance = 0

    def set_latitude(self: Parcelle, lat: int) -> None:
        """Constructeur de parcelle."""
        self.lat = lat

    def set_longitude(self: Parcelle, long: int) -> None:
        """Constructeur de parcelle."""
        self.long = long

    def set_contenance(self: Parcelle, contenance: int) -> None:
        """Constructeur de parcelle."""
        self.contenance = contenance

    def get_address_from_coordinates(self: Parcelle) -> str:
        """Récupère une adresse depuis des coordonnées grâce à Nomatim."""
        logging.debug(
            "Récupère l'adresse avec  lat (%s) et long(%s)",
            self.lat,
            self.long,
        )
        base_url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "format": "json",
            "lat": self.lat,
            "lon": self.long,
        }
        response = requests.get(base_url, params=params, timeout=10)
        data = response.json()
        if "address" in data:
            address = ""
            if "house_number" in data["address"]:
                address = data["address"]["house_number"] + " "
            if "road" in data["address"] and "town" in data["address"]:
                address += data["address"]["road"] + " " + data["address"]["town"]
            else:
                address = data["display_name"]
            self.addresse = address

    def get_infos_from_cadid(self: Parcelle) -> None:
        """Récupère une adresse depuis les infos du cadastre."""
        base_url = "https://api.bdnb.io/v2/gorenove/buildings"
        params = {
            "l_cerffo_idpar": f"cs.{{{self.code_ville}000{self.section}{self.numero}}}",
        }
        response = requests.get(base_url, params=params, timeout=10)
        data = response.json()
        if len(data) > 0:
            if data[0]["adresse_postal"] is not None:
                self.adresse = data[0]["adresse_postal"]
            if data[0]["annee_construction"] is not None:
                self.annee_construction = data[0]["annee_construction"]
            if data[0]["mur_materiau_ff"] is not None:
                self.mur_materiau = data[0]["mur_materiau_ff"]


def get_insee_code(city_name: str) -> str:
    """Récupère le code insee de la ville en argument."""
    if city_name in cacheville:
        logging.info("%s trouvé en cache", city_name)
        return cacheville[city_name]
    logging.info("Cherche la ville %s", city_name)
    base_url = "https://api-adresse.data.gouv.fr/search/"
    params = {"q": city_name, "limit": 1, "type": "municipality", "autocomplete": 0}
    response = requests.get(base_url, params=params, timeout=10)
    data = response.json()
    if data["features"]:
        cacheville[city_name] = data["features"][0]["properties"]["citycode"]
        return data["features"][0]["properties"]["citycode"]
    return None


def get_parcelles_from_town(code_ville: int, contenance: int, seuil: int) -> list:
    """Récupère un lot de parcelle depuis le code insee de la ville."""
    resultats_json = []
    if code_ville in cacheparcelle:
        logging.info("%s trouvé en cache", code_ville)
        resultats_json = cacheparcelle[code_ville]
    else:
        url_api = (
            f"https://apicarto.ign.fr/api/cadastre/parcelle?code_insee={code_ville}"
        )
        start = MAX_RETURNED_API_CARTO
        response = requests.get(url_api, timeout=30)
        response.raise_for_status()
        data = response.json()
        resultats_json.append(data)

        while data["numberReturned"] == MAX_RETURNED_API_CARTO:
            url_api = f"https://apicarto.ign.fr/api/cadastre/parcelle?code_insee={code_ville}&_start={start}"
            logging.debug("url_api %s:", url_api)
            response = requests.get(url_api, timeout=30)
            response.raise_for_status()
            data = response.json()
            resultats_json.append(data)
            start += MAX_RETURNED_API_CARTO
        cacheparcelle[code_ville] = resultats_json

    resultats = []
    for data in resultats_json:
        resultats2 = get_parcelles(
            code_ville,
            data,
        )
        resultats.extend(resultats2)

    seuil = (seuil / 100) * contenance
    new_resultats = []
    for parcelle in resultats:
        if (
            parcelle.contenance is not None
            and abs(parcelle.contenance - contenance) <= seuil
        ):
            new_resultats.append(parcelle)
    logging.info(
        "On a trouvé ",
        len(new_resultats),
        " résultats ayant une surface approchante.",
    )
    return new_resultats


def get_parcelles(
    code_ville: int,
    data: list,
) -> list:
    """Récupère les parcelles ayant la même surface indiqué (par défaut).

    Si on indique un pourcentage alors on retourne les parcelles avoisinantes au % près.
    """
    parcelles_trouvees = []
    for feature in data["features"]:
        section = feature["properties"]["section"]
        numero = feature["properties"]["numero"]
        bbox = feature["properties"]["bbox"]
        long = (bbox[0] + bbox[2]) / 2
        lat = (bbox[1] + bbox[3]) / 2
        parcelle = Parcelle(section, numero, code_ville)
        parcelle.set_latitude(lat)
        parcelle.set_longitude(long)
        parcelle.set_contenance(feature["properties"]["contenance"])
        parcelles_trouvees.append(parcelle)
    return parcelles_trouvees


def main() -> None:
    """Point d'entrée de la fonction."""
    parser = argparse.ArgumentParser(
        description="Recherche de parcelles proches d'une contenance cible.",
    )
    parser.add_argument("ville", help="nom de la ville (tape correctement)")
    parser.add_argument("--annee", help="annee construction")
    parser.add_argument(
        "contenance_cible",
        type=float,
        help="Contenance cible en mètres carrés",
    )
    parser.add_argument(
        "--seuil_percent",
        type=float,
        default=1,
        help="Seuil en pourcentage pour la proximité de contenance",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        type=int,
        choices=[0, 1, 2, 3, 4, 5],
        help="""
    decrease output verbosity. 5 (Critical), 4 (Error), 3 (Warning, default), 2 (Info), 1 (Debug)
    """,  # noqa: E501
    )
    args = parser.parse_args()
    arg_debug = logging.WARNING if args.verbosity is None else args.verbosity * 10
    logging.basicConfig(level=arg_debug)
    try:
        code_ville = get_insee_code(args.ville)
        if code_ville is not None:
            resultats = get_parcelles_from_town(
                code_ville,
                args.contenance_cible,
                args.seuil_percent,
            )
            if resultats:
                print(  # noqa: T201
                    "Parcelles trouvées proches de la contenance cible: ",
                    len(resultats),
                )
                trouve = 0
                with tqdm(
                    total=len(resultats),
                    desc="Détection de l'adresse et des autres facteurs",
                ) as pbar:
                    for parcelle in resultats:
                        suffixe = "Au"
                        parcelle.get_infos_from_cadid()
                        if (
                            not (
                                parcelle is not None
                                and args.annee is not None
                                and parcelle.annee_construction != MINIMUM_DATE
                                and int(parcelle.annee_construction) != int(args.annee)
                            )
                            and parcelle.adresse is not None
                            and parcelle.adresse != ""
                        ):
                            print(  # noqa: T201
                                f"{suffixe} {parcelle.adresse} (cadastre Section: {parcelle.section}, Numéro: {parcelle.numero})",  # noqa: E501
                            )
                            trouve = 1
                        pbar.update(1)
                if trouve == 0:
                    print(  # noqa: T201
                        "Aucun n'a les caractéristiques requises (adresse, année ..etc)",
                    )
            else:
                logging.info("Aucune parcelle trouvée proche de la contenance cible.")
        else:
            logging.error(
                "Nom de ville %s non trouvé. Fais l'effort d'écrire correctement stp, ou de pas vivre un patelin paumé",  # noqa: E501
                {args.ville},
            )

    except requests.RequestException:
        logging.exception("Échec de la requête API avec l'erreur")


if __name__ == "__main__":
    main()
    cacheville.close()
    cacheparcelle.close()
