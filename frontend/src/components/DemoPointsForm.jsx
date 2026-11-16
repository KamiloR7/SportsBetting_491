import { useId, useRef, useState } from "react";
import { mutation } from "../services/api";
export default function DemoPointsForm({onAdded}) {
 const [amount,setAmount]=useState(""),[busy,setBusy]=useState(false),[message,setMessage]=useState(""),[error,setError]=useState("");
 const pending=useRef(null);
 const inputId=useId();
 async function submit(e){e.preventDefault();setBusy(true);setError("");setMessage("");const value=Number(amount);if(!pending.current||pending.current.amount!==value)pending.current={amount:value,request_key:crypto.randomUUID()};try{const wallet=await mutation("/wallet/demo-topup",pending.current);pending.current=null;setMessage(`Added ${value.toLocaleString()} points. New balance: ${wallet.balance.toLocaleString()} points.`);setAmount("");window.dispatchEvent(new Event("wallet-updated"));onAdded?.();}catch(e){setError(e.message);if(e.status>=400&&e.status<500)pending.current=null;}finally{setBusy(false);}}
 return <form className="demo-points-form" onSubmit={submit}><label htmlFor={inputId}>How many demo points would you like?</label><div className="amount-entry"><input id={inputId} type="number" min="1" max="1000000" step="1" placeholder="Enter an amount, e.g. 250" required disabled={busy} value={amount} onChange={e=>setAmount(e.target.value)}/><button className="primary-button" disabled={busy}>{busy?"Adding…":"Add points"}</button></div><p>Choose 1–1,000,000 whole virtual points. No cash value.</p>{message&&<p className="success-banner" role="status">{message}</p>}{error&&<p role="alert">{error}</p>}</form>;
}
