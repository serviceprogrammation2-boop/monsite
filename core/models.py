from django.db import models

class Employe(models.Model):
    mat_emp = models.CharField(max_length=10, primary_key=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nom} {self.prenom}"


class Ligne(models.Model):
    code_ligne = models.CharField(max_length=10, primary_key=True)
    description = models.CharField(max_length=200)

    def __str__(self):
        return self.description


class Equipement(models.Model):
    code_equip = models.CharField(max_length=10, primary_key=True)
    designation = models.CharField(max_length=100)

    def __str__(self):
        return self.designation


class Navette(models.Model):
    nda = models.CharField(max_length=10, primary_key=True)
    ligne = models.ForeignKey(Ligne, on_delete=models.CASCADE)
    chauffeur = models.ForeignKey(Employe, on_delete=models.SET_NULL, null=True, blank=True)
    vehicule = models.ForeignKey(Equipement, on_delete=models.SET_NULL, null=True, blank=True)
    date_service = models.DateField()

    def __str__(self):
        return f"Navette {self.nda}"
