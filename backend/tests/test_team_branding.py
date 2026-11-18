from types import SimpleNamespace
from urllib.parse import urlsplit
from app.services.team_branding import team_brand,match_brand_fields,clean_color,clean_logo,build_index


def test_known_teams_and_historical_names_resolve_to_the_same_verified_profile():
    assert team_brand("MLB","D-backs")["name"]=="Arizona Diamondbacks"
    bengals=team_brand("National Football League","Cincinnati Bengals")
    assert bengals["primary_color"]=="#fb4f14"
    assert urlsplit(bengals["logo_url"]).netloc=="a.espncdn.com"
    assert team_brand("English Premier League","Coventry")["provider_id"]==team_brand("EPL","Coventry City")["provider_id"]
    assert team_brand("EPL","Hull")["provider_id"]==team_brand("EPL","Hull City")["provider_id"]
    assert team_brand("MLB","Oakland Athletics")["provider_id"]==team_brand("MLB","Athletics")["provider_id"]
    for name in ["Burnley","Leicester City","Luton Town","Sheffield United","Southampton","West Ham United","Wolverhampton Wanderers"]:
        assert team_brand("EPL",name)["logo_url"]


def test_unknown_team_does_not_get_guessed_colors_or_another_teams_logo():
    assert team_brand("NFL","Unknown Team")=={}
    assert team_brand("MLB","Cincinnati Bengals")=={}
    fields=match_brand_fields("NFL","Unknown Team","Cincinnati Bengals")
    assert fields["home_logo_url"] is None and fields["home_primary_color"] is None
    assert fields["away_primary_color"]=="#fb4f14"


def test_unsafe_colors_and_logo_urls_are_rejected():
    assert clean_color("aBc123")=="#abc123"
    for value in ["red","#ffffff","url(example.com)",None]:assert clean_color(value) is None
    for url in ["http://a.espncdn.com/i/teamlogos/logo.png","https://a.espncdn.com.evil.test/i/teamlogos/logo.png","javascript:alert(1)","https://a.espncdn.com/not-team-data.png"]:assert clean_logo(url) is None
    assert clean_logo("https://a.espncdn.com/i/teamlogos/nfl/500/cin.png")


def test_ambiguous_alias_is_not_assigned_to_either_team():
    a={"league":"EPL","provider_id":"1","aliases":["United"]}
    b={"league":"EPL","provider_id":"2","aliases":["United"]}
    assert build_index([a,b])[("EPL","united")] is None
