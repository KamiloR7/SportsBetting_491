import { Link, NavLink, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { getParlayDraft } from "../services/parlayDraft";
const tabs=[["/dashboard","Explore games"],["/insights","Model insights"],["/parlay","Parlay builder"],["/bets/active","Active bets"],["/bets/history","Bet history"],["/wallet","Wallet activity"]];
export default function AppFrame({children}){
 const location=useLocation(),[count,setCount]=useState(()=>getParlayDraft().length);
 useEffect(()=>{const target=location.hash?document.getElementById(location.hash.slice(1)):null;if(target)target.scrollIntoView();else window.scrollTo(0,0);},[location.pathname,location.hash]);
 useEffect(()=>{const update=()=>setCount(getParlayDraft().length);window.addEventListener("parlay-updated",update);window.addEventListener("storage",update);return()=>{window.removeEventListener("parlay-updated",update);window.removeEventListener("storage",update);};},[]);
 return <div className="app-frame"><header className="site-header"><Link to="/dashboard" className="brand"><span className="brand-mark">V</span>VIGOR<span className="brand-tag">THE SPORTS LAB</span></Link><nav aria-label="Main navigation">{tabs.map(([path,title])=><NavLink key={path} to={path}>{title}{path==="/parlay"&&count>0&&<span className="nav-count">{count}</span>}</NavLink>)}</nav></header>{children}<footer className="site-footer"><span className="brand">VIGOR</span><span>Real games. Measured predictions. Virtual points.</span><span>University project · No cash value</span></footer></div>;
}
