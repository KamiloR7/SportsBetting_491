function BettingOptions({ match, onSelectBet }) {
  const isPremierLeague =
    match.league === "Premier League";

  return (
    <div className="betting-options">

      <h2>Betting Options</h2>

      {isPremierLeague ? (
        <div className="betting-market">

          <h3>Match Result</h3>

          <button
            onClick={() =>
              onSelectBet({
                matchId: match.id,
                match:
                  `${match.homeTeam} vs ${match.awayTeam}`,
                market: "Match Result",
                selection: match.homeTeam,
                odds: match.odds.homeWin,
              })
            }
          >
            {match.homeTeam}
            {" "}
            {match.odds.homeWin}
          </button>

          <button
            onClick={() =>
              onSelectBet({
                matchId: match.id,
                match:
                  `${match.homeTeam} vs ${match.awayTeam}`,
                market: "Match Result",
                selection: "Draw",
                odds: match.odds.draw,
              })
            }
          >
            Draw {match.odds.draw}
          </button>

          <button
            onClick={() =>
              onSelectBet({
                matchId: match.id,
                match:
                  `${match.homeTeam} vs ${match.awayTeam}`,
                market: "Match Result",
                selection: match.awayTeam,
                odds: match.odds.awayWin,
              })
            }
          >
            {match.awayTeam}
            {" "}
            {match.odds.awayWin}
          </button>

        </div>
      ) : (
        <>
          <div className="betting-market">

            <h3>Moneyline</h3>

            <button
              onClick={() =>
                onSelectBet({
                  matchId: match.id,
                  match:
                    `${match.homeTeam} vs ${match.awayTeam}`,
                  market: "Moneyline",
                  selection:
                    match.homeTeam,
                  odds:
                    match.odds
                      .homeMoneyline,
                })
              }
            >
              {match.homeTeam}
              {" "}
              {match.odds.homeMoneyline}
            </button>

            <button
              onClick={() =>
                onSelectBet({
                  matchId: match.id,
                  match:
                    `${match.homeTeam} vs ${match.awayTeam}`,
                  market: "Moneyline",
                  selection:
                    match.awayTeam,
                  odds:
                    match.odds
                      .awayMoneyline,
                })
              }
            >
              {match.awayTeam}
              {" "}
              {match.odds.awayMoneyline}
            </button>

          </div>

          <div className="betting-market">

            <h3>Point Spread</h3>

            <button
              onClick={() =>
                onSelectBet({
                  matchId: match.id,
                  match:
                    `${match.homeTeam} vs ${match.awayTeam}`,
                  market: "Spread",
                  selection:
                    `${match.homeTeam} ${match.odds.homeSpread}`,
                  odds: "-110",
                })
              }
            >
              {match.homeTeam}
              {" "}
              {match.odds.homeSpread}
            </button>

            <button
              onClick={() =>
                onSelectBet({
                  matchId: match.id,
                  match:
                    `${match.homeTeam} vs ${match.awayTeam}`,
                  market: "Spread",
                  selection:
                    `${match.awayTeam} ${match.odds.awaySpread}`,
                  odds: "-110",
                })
              }
            >
              {match.awayTeam}
              {" "}
              {match.odds.awaySpread}
            </button>

          </div>

          <div className="betting-market">

            <h3>
              Total: {match.odds.total}
            </h3>

            <button
              onClick={() =>
                onSelectBet({
                  matchId: match.id,
                  match:
                    `${match.homeTeam} vs ${match.awayTeam}`,
                  market: "Total",
                  selection:
                    `Over ${match.odds.total}`,
                  odds:
                    match.odds.overOdds,
                })
              }
            >
              Over {match.odds.total}
              {" "}
              {match.odds.overOdds}
            </button>

            <button
              onClick={() =>
                onSelectBet({
                  matchId: match.id,
                  match:
                    `${match.homeTeam} vs ${match.awayTeam}`,
                  market: "Total",
                  selection:
                    `Under ${match.odds.total}`,
                  odds:
                    match.odds.underOdds,
                })
              }
            >
              Under {match.odds.total}
              {" "}
              {match.odds.underOdds}
            </button>

          </div>
        </>
      )}

    </div>
  );
}

export default BettingOptions;