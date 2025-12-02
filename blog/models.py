# blog/models.py
from django.db import models


class Ligne(models.Model):
    code = models.CharField(max_length=10, primary_key=True)
    origine = models.CharField(max_length=100)
    dest = models.CharField(max_length=100)
    agence = models.CharField(max_length=50, null=True, blank=True)
    klm = models.IntegerField(null=True, blank=True)
    actif = models.SmallIntegerField(default=1)

    sortie = models.IntegerField(null=True, blank=True)
    ord = models.IntegerField(null=True, blank=True)
    

    nch = models.IntegerField(null=True, blank=True)
    client = models.CharField(max_length=100, null=True, blank=True)


    sv = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'ligne'
        managed = False



class Employe(models.Model):
    mat_emp = models.CharField(max_length=50, primary_key=True)
    nom_emp = models.CharField(max_length=200)

    class Meta:
        db_table = 'employe'
        managed = False

    def __str__(self):
        return self.nom_emp


class Navette(models.Model):
    id = models.AutoField(primary_key=True)
    ligne = models.ForeignKey(
        Ligne,
        to_field='code',
        db_column='ligne',
        on_delete=models.DO_NOTHING
    )
    asens = models.CharField(max_length=5)
    atypsrv = models.CharField(max_length=5)
    nda = models.IntegerField()
    adatserv = models.DateTimeField()
    achauffeur = models.ForeignKey(
        Employe,
        db_column='achauffeur',
        to_field='mat_emp',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="navettes_principales"
    )
    rchauffeur = models.ForeignKey(
        Employe,
        db_column='rchauffeur',
        to_field='mat_emp',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="navettes_retour"
    )
    aveh = models.CharField(max_length=50, null=True, blank=True)
    rveh = models.CharField(max_length=50, null=True, blank=True)
    ags = models.CharField(max_length=50, null=True, blank=True)
    rem = models.CharField(max_length=50, null=True, blank=True)
    ndr = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'navette'
        managed = False
        unique_together = ('ligne', 'asens', 'atypsrv', 'adatserv')

    def __str__(self):
        return f"Navette {self.id} - {self.ligne.code} ({self.adatserv:%Y-%m-%d})"
from django.db import models

class Equipement(models.Model):
    cod_equ = models.CharField(max_length=50, primary_key=True)
    dat_mod_equ = models.DateField(null=True, blank=True)
    des_equ = models.CharField(max_length=255, null=True, blank=True)
    dat_aqu_equ = models.DateField(null=True, blank=True)
    mnt_aqu_equ = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    cou_arr_equ = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    dat_fin_gar_equ = models.DateField(null=True, blank=True)
    uni_cou_arr_equ = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    dat_ins_equ = models.DateField(null=True, blank=True)
    ref_fab_equ = models.CharField(max_length=100, null=True, blank=True)
    mrq_equ = models.CharField(max_length=100, null=True, blank=True)
    mai_ext_equ = models.CharField(max_length=1, null=True, blank=True)
    int_sur_aut_equ = models.CharField(max_length=1, null=True, blank=True)
    ann_fab_equ = models.IntegerField(null=True, blank=True, default=0)
    cod_inv_equ = models.CharField(max_length=50, null=True, blank=True)
    mod_equ = models.CharField(max_length=100, null=True, blank=True)
    emp_equ = models.CharField(max_length=100, null=True, blank=True)
    obs_equ = models.CharField(max_length=255, null=True, blank=True)
    anc_cod_equ = models.CharField(max_length=50, null=True, blank=True)
    per_amo_equ = models.IntegerField(null=True, blank=True, default=0)
    eta_equ = models.CharField(max_length=1, null=True, blank=True)
    fab_equ = models.CharField(max_length=100, null=True, blank=True)
    num_ser_equ = models.CharField(max_length=100, null=True, blank=True)
    imm_equ = models.CharField(max_length=100, null=True, blank=True)
    fra_acc_equ = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    cod_fon = models.CharField(max_length=50, null=True, blank=True)
    cod_cri = models.CharField(max_length=50, null=True, blank=True)
    cod_loc = models.CharField(max_length=50, null=True, blank=True)
    cod_fam_equ = models.CharField(max_length=50, null=True, blank=True)
    cod_equ_per = models.CharField(max_length=50, null=True, blank=True)
    cod_fou = models.CharField(max_length=50, null=True, blank=True)
    cod_sta = models.SmallIntegerField()
    dat_sta_equ = models.DateField(null=True, blank=True)
    dat_cre_equ = models.DateField(null=True, blank=True)
    use_cre_equ = models.CharField(max_length=50, null=True, blank=True)
    use_mod_equ = models.CharField(max_length=50, null=True, blank=True)
    mnt_amo_equi = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    eta_phy_equ = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = "equipement"

    def __str__(self):
        return f"{self.cod_equ} - {self.des_equ or ''}"

class Locatile(models.Model):
    cod_loc = models.CharField(max_length=5, primary_key=True)
    lib_loc = models.CharField(max_length=100, null=True, blank=True)
    adr_loc = models.CharField(max_length=100, null=True, blank=True)
    cod_loc_loc = models.CharField(max_length=5, null=True, blank=True)
    cod_vil = models.IntegerField(null=True, blank=True)

    class Meta:
        managed = False      # 👈 Empêche Django de toucher à la table
        db_table = 'locatile'  # 👈 Nom exact dans ta base PostgreSQL
