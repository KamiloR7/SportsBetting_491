const mockMatches = [
{
    id: 1,
    league: "NBA",
    homeTeam: "Lakers",
    awayTeam: "Warriors",
    date: "Oct 20",
    time: "7:30 PM",

    probabilities: {
      homeWin: 46,
      awayWin: 54,
    },

    odds: {
      homeMoneyline: "+120",
      awayMoneyline: "-105",

      homeSpread: "+3.5",
      awaySpread: "-3.5",

      total: 225.5,
      overOdds: "-110",
      underOdds: "-110",
    },
  },

  {
    id: 2,
    league: "NFL",
    homeTeam: "Chiefs",
    awayTeam: "Bills",
    date: "Oct 21",
    time: "5:20 PM",

    probabilities: {
      homeWin: 58,
      awayWin: 42,
    },

    odds: {
      homeMoneyline: "-125",
      awayMoneyline: "+110",

      homeSpread: "-2.5",
      awaySpread: "+2.5",

      total: 47.5,
      overOdds: "-110",
      underOdds: "-110",
    },
  },

  {
    id: 3,
    league: "Premier League",
    homeTeam: "Arsenal",
    awayTeam: "Chelsea",
    date: "Oct 22",
    time: "12:30 PM",

    probabilities: {
      homeWin: 41,
      draw: 27,
      awayWin: 32,
    },

    odds: {
      homeWin: "+130",
      draw: "+240",
      awayWin: "+190",
    },
  },
];

export default mockMatches;