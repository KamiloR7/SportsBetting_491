import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest, mutation } from "../services/api";
import { addParlayLeg } from "../services/parlayDraft";
export default function BetSlip({match, initialSelection = null, onBusyChange}) {
 const [markets,setMarkets]=useState(null),[error,setError]=useState(""),[authRequired,setAuthRequired]=useState(false),[selected,setSelected]=useState(null),[stake,setStake]=useState("100"),[busy,setBusy]=useState(false),[receipt,setReceipt]=useState(null);
 const pending=useRef(null);
 const [parlayMessage,setParlayMessage]=useState("");
 const [now,setNow]=useState(()=>Date.now());
 useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer);},[]);
 useEffect(()=>{const controller=new AbortController();apiRequest(`/matches/${match.id}/markets`,{signal:controller.signal}).then(data=>{if(controller.signal.aborted)return;setMarkets(data);const pick=data.filter(m=>m.is_open&&m.odds_source==="model_derived").flatMap(m=>m.outcomes).find(o=>o.selection===initialSelection);if(pick)setSelected(pick);}).catch(e=>{if(!controller.signal.aborted)setError(e.message);});return()=>controller.abort();},[match.id,initialSelection]);
 function refresh(){setError("");setSelected(null);setMarkets(null);apiRequest(`/matches/${match.id}/markets`).then(setMarkets).catch(e=>setError(e.message));}
 const open=markets?.filter(m=>m.is_open)||[];
 const market=open[0]||markets?.[0];
 const reconstructed=market?.odds_source==="model_reconstructed";
 const modelPriced=market?.odds_source==="model_derived"||reconstructed;
 const canBet=match.status==="scheduled"&&Date.parse(match.start_time)>now;
 const parts=String(selected?.decimal_odds||"0").split(".");
 const scaled=BigInt(parts[0])*10000n+BigInt((parts[1]||"").padEnd(4,"0").slice(0,4));
 const payout=selected&&/^[1-9]\d{0,6}$/.test(stake)?Number(BigInt(stake)*scaled/10000n):null;
 async function submit(e){
  e.preventDefault();if(!selected||busy)return;setBusy(true);onBusyChange?.(true);setError("");setAuthRequired(false);
  const payload={match_id:match.id,outcome_id:selected.id,stake:Number(stake),expected_odds:selected.decimal_odds};const signature=JSON.stringify(payload);
  if(!pending.current||pending.current.signature!==signature)pending.current={signature,body:{...payload,request_key:crypto.randomUUID()}};
  try{const result=await mutation("/bets",pending.current.body);setReceipt(result);pending.current=null;setSelected(null);window.dispatchEvent(new Event("wallet-updated"));}
  catch(e){setError(e.message);setAuthRequired(e.status===401);if(e.status>=400&&e.status<500)pending.current=null;}finally{setBusy(false);onBusyChange?.(false);}
 }
 function addToParlay(){if(!selected)return;try{addParlayLeg({match_id:match.id,outcome_id:selected.id,expected_odds:selected.decimal_odds,selection:selected.selection,selection_name:name(selected.selection),home_team_name:match.home_team_name,away_team_name:match.away_team_name,start_time:match.start_time});setParlayMessage("Selection added. Choose another game to complete your parlay.");setError("");}catch(e){setError(e.message);}}
 const name=selection=>selection==="home"?match.home_team_name:selection==="away"?match.away_team_name:"Draw";
 return <section className="bet-slip"><span className="section-kicker">THE BET SLIP</span><h2>Back your pick.</h2><p>{modelPriced?"Model-priced match winner · virtual points":"Match winner · virtual points"}</p>{!canBet&&<p>Betting is closed for this match.</p>}{reconstructed&&<div className="closed-model-preview"><h3>Reconstructed pregame model odds</h3><p>{market.preview_note}</p><div className="browse-odds">{market.outcomes.map(o=><span key={o.id ?? o.selection}><small>{name(o.selection)}</small><strong>{Number(o.decimal_odds).toFixed(2)}</strong></span>)}</div></div>}{markets===null&&!error&&<p role="status">Calculating model prices…</p>}{markets&&!open.length&&<p>No open market is available for this match.</p>}{canBet&&open.map(m=><div key={m.market_id} className="outcome-grid">{m.outcomes.map(o=><button disabled={busy} type="button" aria-pressed={selected?.id===o.id} key={o.id ?? o.selection} onClick={()=>{setSelected(o);setReceipt(null);}}><span>{name(o.selection)}{m.probabilities&&<small>{(m.probabilities[o.selection]*100).toFixed(1)}% model probability</small>}</span><strong>{Number(o.decimal_odds).toFixed(2)}</strong></button>)}</div>)}
 {modelPriced&&<div className="pricing-context"><p>Prices include a {(market.pricing_margin*100).toFixed(0)}% pricing margin. {match.league_name?.includes("Premier")?"Home / draw / away.":"Two-way winner; ties refunded."}</p><p>{reconstructed?"Reconstructed":"Quoted"} {new Date(market.quoted_at).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})} · {reconstructed?"Display only; no in-play updates.":"Odds locked when your bet is accepted."}</p><details><summary>How are these prices calculated?</summary><p>Fair decimal odds are 1 ÷ model probability. Offered odds apply the pricing margin, then round down to two decimals. These are our model estimates, rather than bookmaker feed prices. Payouts include your stake and round down to whole points.</p></details></div>}
 {canBet&&<button className="text-button refresh-prices" type="button" disabled={busy} onClick={refresh}>Refresh prices ↻</button>}
 {selected&&canBet&&<form onSubmit={submit}><p className="selected-pick">{name(selected.selection)} <strong>@ {Number(selected.decimal_odds).toFixed(2)}</strong></p><label>Stake in points<input type="number" min="1" max="1000000" step="1" required value={stake} disabled={busy} onChange={e=>setStake(e.target.value)}/></label><div className="payout-preview"><span>Total return<strong>{payout??"—"} pts</strong></span><span>Profit if won<strong>{payout?Math.max(0,payout-Number(stake)):"—"} pts</strong></span></div><div className="bet-actions"><button disabled={busy||!payout}>{busy?"Placing…":"Place single bet"}</button>{modelPriced&&<button type="button" className="secondary-button" disabled={busy} onClick={addToParlay}>Add to parlay +</button>}</div></form>}
 {parlayMessage&&<p className="success-banner" role="status">{parlayMessage} <Link to="/parlay">View parlay →</Link></p>}
 {error&&<p role="alert">{error} {authRequired&&<Link to="/login">Sign in</Link>}</p>}{receipt&&<p role="status">Bet #{receipt.id} accepted: {receipt.stake} points on {name(receipt.selection)} at {Number(receipt.accepted_odds).toFixed(2)}. Total return if won: {receipt.potential_payout} points. {receipt.status}.</p>}</section>;
}
