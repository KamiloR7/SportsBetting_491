import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest, mutation } from "../services/api";
import DemoPointsForm from "./DemoPointsForm";
export default function AccountPanel({showTopup=true}){
 const [state,setState]=useState({loading:true}),[adding,setAdding]=useState(false);
 const refresh=useCallback(async()=>{try{const user=await apiRequest("/auth/me");const wallet=await apiRequest("/wallet");setState({user,wallet});}catch(e){setState({error:e.message,status:e.status});}},[]);
 useEffect(()=>{let active=true;Promise.resolve().then(()=>{if(active)refresh();});const update=()=>refresh();window.addEventListener("wallet-updated",update);const timer=setInterval(update,30000);return()=>{active=false;clearInterval(timer);window.removeEventListener("wallet-updated",update);};},[refresh]);
 if(state.loading)return <p role="status">Loading account…</p>;
 if(!state.user)return <aside className="account-panel guest-account"><div><span className="section-kicker">MAKE YOUR FIRST PICK</span><h2>1,000 points. A fresh start.</h2><p>{state.status===401?"Create an account to place picks and track your results.":state.error}</p></div><Link className="guest-join" to="/login">Join the game ↗</Link></aside>;
 return <section className="account-panel"><div className="account-heading"><div><strong>{state.user.email}</strong><Link to="/wallet"><h2>{state.wallet.balance.toLocaleString()} <span>PTS ↗</span></h2></Link></div><div className="wallet-actions">{showTopup&&<button aria-expanded={adding} onClick={()=>setAdding(!adding)}>{adding?"Close":"+ Demo points"}</button>}<button onClick={async()=>{try{await mutation("/auth/logout",{});window.dispatchEvent(new Event("wallet-updated"));await refresh();}catch(e){setState(s=>({...s,error:e.message}));}}}>Sign out</button></div></div><p>Virtual points · no cash value</p>{adding&&<DemoPointsForm/>}{state.error&&<p role="alert">{state.error}</p>}</section>;
}
