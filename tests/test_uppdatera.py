"""Uppdateringen rör användarens riktiga mapp. Den testas därför mot just de lägen som uppstått på riktigt."""
import uppdatera as u

APPFILER = ("app.py", "avlasning.py", "kontroller.py", "config.py")


def _app(mapp, version):
    mapp.mkdir(parents=True, exist_ok=True)
    for f in APPFILER:
        (mapp / f).write_text(f"# {f} version {version}\n", encoding="utf8")
    (mapp / ".streamlit").mkdir(exist_ok=True)
    (mapp / ".streamlit" / "config.toml").write_text(f"# tema {version}\n", encoding="utf8")
    return mapp


def _installation(tmp_path, version="gammal"):
    inst = _app(tmp_path / "Documents" / "matarapp", version)
    (inst / ".streamlit" / "secrets.toml").write_text("ANTHROPIC_API_KEY = 'sk-ant-min-riktiga'\n", encoding="utf8")
    (inst / ".venv" / "Scripts").mkdir(parents=True)
    (inst / ".venv" / "Scripts" / "python.exe").write_text("miljö", encoding="utf8")
    (inst / "__pycache__").mkdir()
    (inst / "__pycache__" / "app.cpython-312.pyc").write_bytes(b"x")
    (inst / "kontroll_resultat.txt").write_text("mitt resultat", encoding="utf8")
    return inst


def test_ny_version_laggs_pa_ratt_plats_och_nyckel_och_miljo_ar_ororda(tmp_path):
    inst = _installation(tmp_path)
    ny = _app(tmp_path / "Downloads" / "kvittens_v3_12" / "matarapp", "NY")
    (ny / ".streamlit" / "secrets.toml").write_text("ANTHROPIC_API_KEY = 'PLATSHÅLLARE'\n", encoding="utf8")   # får aldrig skriva över
    (ny / "uppdatera.py").write_text("# ny fil\n", encoding="utf8")
    rader = []
    assert u.main(ny, inst, rader.append) == 0
    assert (inst / "app.py").read_text(encoding="utf8") == "# app.py version NY\n"
    assert (inst / ".streamlit" / "config.toml").read_text(encoding="utf8") == "# tema NY\n" and (inst / "uppdatera.py").exists()
    assert "min-riktiga" in (inst / ".streamlit" / "secrets.toml").read_text(encoding="utf8")
    assert (inst / ".venv" / "Scripts" / "python.exe").read_text(encoding="utf8") == "miljö"
    assert (inst / "kontroll_resultat.txt").read_text(encoding="utf8") == "mitt resultat"
    assert not (inst / "__pycache__").exists() and any("GitHub Desktop" in r for r in rader)


def test_dubblettkopian_flyttas_undan_men_raderas_inte(tmp_path):
    """Det som granskningen hittade: samma filer både i roten och i matarapp/matarapp."""
    inst = _installation(tmp_path)
    _app(inst / "matarapp", "dubblett")
    (inst / "matarapp" / "__pycache__").mkdir()
    ny = _app(tmp_path / "Downloads" / "ny" / "matarapp", "NY")
    rader = []
    assert u.main(ny, inst, rader.append) == 0
    assert not (inst / "matarapp").exists()
    (undan,) = [m for m in inst.parent.iterdir() if m.name.startswith("matarapp_gammal_kopia_")]
    assert (undan / "app.py").read_text(encoding="utf8") == "# app.py version dubblett\n"          # inget är raderat
    assert any("FLYTTAD (inte raderad)" in r for r in rader)


def test_nyckel_som_bara_finns_i_den_inre_kopian_raddas(tmp_path):
    inst = _app(tmp_path / "Documents" / "matarapp", "gammal")
    (inst / ".git").mkdir()
    inre = _app(inst / "matarapp", "inre")
    (inre / ".streamlit" / "secrets.toml").write_text("ANTHROPIC_API_KEY = 'sk-ant-låg-här'\n", encoding="utf8")
    ny = _app(tmp_path / "ny" / "matarapp", "NY")
    assert u.main(ny, inst, lambda r: None) == 0
    assert "låg-här" in (inst / ".streamlit" / "secrets.toml").read_text(encoding="utf8")


def test_installationen_hittas_och_en_nyuppackad_mapp_forvaxlas_inte_med_den(tmp_path):
    assert u.hitta_installation(tmp_path) is None
    _app(tmp_path / "Documents" / "matarapp", "bara filer")                       # ingen .venv, ingen nyckel, ingen .git
    assert u.hitta_installation(tmp_path) is None
    inst = _installation(tmp_path)
    assert u.hitta_installation(tmp_path) == inst


def test_begripliga_stopp(tmp_path):
    rader = []
    assert u.main(tmp_path, None, rader.append) == 1 and "ser inte ut att innehålla appen" in "".join(rader)
    inst = _installation(tmp_path)
    rader.clear()
    assert u.main(inst, inst, rader.append) == 0 and "ÄR din installation" in "".join(rader)       # körd i fel mapp: städar bara


def test_skyddade_filer():
    from pathlib import Path
    for p in (".streamlit/secrets.toml", ".streamlit/secrets.toml.example", ".venv/x", "__pycache__/a.pyc", "kontroll_resultat.txt", ".git/config"):
        assert u.skyddad(Path(p)), p
    for p in ("app.py", ".streamlit/config.toml", "testbilder/facit.json", "static/ikon.png"):
        assert not u.skyddad(Path(p)), p
