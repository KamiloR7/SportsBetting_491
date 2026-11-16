"""Owner-scoped wallet descriptions and links to the originating tickets."""
from sqlalchemy import text, bindparam


def describe_activity(db, user_id, rows):
    ids={"bet":set(),"parlay":set()}
    def reference(row):
        parts=row["reference"].split(":")
        if len(parts)==3 and parts[0] in ids and parts[1].isdigit():
            value=int(parts[1])
            if 0 < value < 2**63: return parts[0],value
        return None,None
    for row in rows:
        kind,ticket_id=reference(row)
        if kind:ids[kind].add(ticket_id)
    singles={};parlays={};legs={}
    if ids["bet"]:
        query=text("""SELECT b.id,b.status,b.selection,b.stake,b.accepted_odds,m.id AS match_id,
            ht.name AS home_team,at.name AS away_team FROM virtual_bets b
            JOIN matches m ON m.id=b.match_id JOIN teams ht ON ht.id=m.home_team_id
            JOIN teams at ON at.id=m.away_team_id WHERE b.user_id=:uid AND b.id IN :ids""").bindparams(bindparam("ids",expanding=True))
        singles={row["id"]:dict(row) for row in db.execute(query,{"uid":user_id,"ids":sorted(ids["bet"])}).mappings()}
    if ids["parlay"]:
        query=text("SELECT id,status,stake,combined_odds FROM virtual_parlays WHERE user_id=:uid AND id IN :ids").bindparams(bindparam("ids",expanding=True))
        parlays={row["id"]:dict(row) for row in db.execute(query,{"uid":user_id,"ids":sorted(ids["parlay"])}).mappings()}
        if parlays:
            query=text("""SELECT pl.parlay_id,pl.selection,ht.name AS home_team,at.name AS away_team
                FROM virtual_parlay_legs pl JOIN virtual_parlays p ON p.id=pl.parlay_id
                JOIN matches m ON m.id=pl.match_id JOIN teams ht ON ht.id=m.home_team_id
                JOIN teams at ON at.id=m.away_team_id WHERE p.user_id=:uid AND p.id IN :ids ORDER BY pl.id""").bindparams(bindparam("ids",expanding=True))
            for row in db.execute(query,{"uid":user_id,"ids":sorted(parlays)}).mappings():
                legs.setdefault(row["parlay_id"],[]).append(dict(row))
    result=[]
    for original in rows:
        row=dict(original);kind=row["kind"]
        row.update(title=kind.replace("_"," ").title(),source_label="From virtual points" if row["amount"]>0 else "To virtual betting",description="Virtual points only.",ticket_type=None,ticket_id=None,ticket_status=None)
        if kind=="INITIAL":row.update(title="Starting points",source_label="From account setup",description="Your opening virtual-point balance.")
        elif kind=="DEMO_TOPUP":row.update(title="Demo points added",source_label="From demo points",description=f"You added {row['amount']:,} virtual points.")
        elif kind=="DEMO_RESET":row.update(title="Demo wallet reset",source_label="From a fresh demo round",description="Opening balance after your confirmed wallet and bet reset.")
        ticket_kind,ticket_id=reference(row)
        ticket=singles.get(ticket_id) if ticket_kind=="bet" else parlays.get(ticket_id) if ticket_kind=="parlay" else None
        if ticket:
            single=ticket_kind=="bet"
            direction="To" if row["amount"]<0 else "From"
            if single:
                pick="Draw" if ticket["selection"]=="draw" else ticket["home_team"] if ticket["selection"]=="home" else ticket["away_team"]
                label=f"single bet #{ticket_id}"
                description=f"{ticket['home_team']} vs {ticket['away_team']} · Pick: {pick} · {ticket['stake']:,} points @ {float(ticket['accepted_odds']):.2f}"
            else:
                selections=legs.get(ticket_id,[])
                label=f"{len(selections)}-leg parlay #{ticket_id}"
                picks=["Draw" if leg["selection"]=="draw" else leg["home_team"] if leg["selection"]=="home" else leg["away_team"] for leg in selections]
                description=" + ".join(picks[:2])+(f" + {len(picks)-2} more" if len(picks)>2 else "")+f" · {ticket['stake']:,} points @ {float(ticket['combined_odds']):.4f} combined"
            title=("Parlay stake placed" if not single else "Single-bet stake placed") if row["amount"]<0 else ("Stake refunded" if kind in {"REFUND","PARLAY_REFUND"} else "Winning parlay payout" if not single else "Winning bet payout")
            if kind in {"PAYOUT","PARLAY_PAYOUT"}:description+=" · Return includes the original stake."
            row.update(title=title,source_label=f"{direction} {label}",description=description,ticket_type="single" if single else "parlay",ticket_id=ticket_id,ticket_status=ticket["status"])
        result.append(row)
    return result
