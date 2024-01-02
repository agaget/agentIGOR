# Agent IGOR
>I'm here to serve my sweet master

Agent Igor va piocher dans différente API open source pour trouver des adresses en fonctions d'infos que vous pouvez donner depuis une annonce immobilière
https://apicarto.ign.fr
https://api-adresse.data.gouv.fr
https://api.bdnb.io/v2/gorenove
https://nominatim.openstreetmap.org

Pourquoi autant ? Bah y'a peut-être moyen de faire avec moins, mais je t'en prie dis moi.

## Poetry execution
Poetry c'est le sang ! (pour faire du python tout du moins)\
Voir doc officielle pour installation : https://python-poetry.org/docs/

```
> poetry install
> poetry run agentigor <nom_ville> <surface en m²> 
```

##Exemple:
Voici un exemple d'annonce sur seloger.com, on trouve facilement l'info de la **surface du terrain** (pas la surface loi carez, ça j'ai pas trouvé de base de donnée) et facultativement mais ça réduit pas mal le champ des possibles l'**année de construction**.
![](img/exemple.png "Annonce se loger").

On execute du coup le script, on précise le **seuil_percent** pour dire qu'on veut la surface exacte. Effectivement des fois les agents immobiliers donnent une approximation. 
```bash
poetry run agentigor palaiseau 601 --annee 1980 --seuil_percent 0
```

Le script retourne alors dans la console une adresse (pour cet exemple).

Plus la ville est grande, plus ça prendra du temps et plus vous risquez d'avoir beaucoup de résultat. Plus le terrain est petit plus vous avez de résultat parce que dans la vie il y a plus de gens avec des petits terrains qu'avec des grands.

> :warning:  Ne marche pas pour les apparts du coup !

Et puis des fois on fait chou blanc, c'est comme ça...

Un jour je rajouterais peut-être le diagnostics qui apparaît des fois dans les annonces, il est dans la base de donnée.