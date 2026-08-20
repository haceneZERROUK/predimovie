# Test du parsing du fichier IMDb : pas besoin de réseau, on utilise
# un petit extrait de TSV directement dans le test.
from data_engineering.imdb import extraire_notes_imdb

TSV_EXEMPLE = "tconst\taverageRating\tnumVotes\ntt1160419\t8.0\t1077956\ntt0000001\t5.7\t2220\n"


def test_extraire_notes_imdb():
    notes = extraire_notes_imdb(TSV_EXEMPLE)

    assert notes["tt1160419"] == 8.0
    assert notes["tt0000001"] == 5.7
    assert len(notes) == 2
