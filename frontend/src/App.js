import React, { useState, useEffect } from "react";
import axios from "axios";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, Radar
} from "recharts";

const API = "https://intelli-credit-5x1a.onrender.com";

const C = {
  bg:"#0a0f1e", surface:"#0f1729", card:"#161f35", border:"#1e2d4a",
  accent:"#0ea5e9", teal:"#0d9488", green:"#10b981", amber:"#f59e0b",
  red:"#ef4444", text:"#e2e8f0", muted:"#64748b", subtle:"#94a3b8", purple:"#7c3aed",
};

const decisionColor = (d="")=>{
  if(!d||d==="N/A") return C.muted;
  if(d.includes("Reject")) return C.red;
  if(d.includes("Strict")||d.includes("Condition")) return C.amber;
  return C.green;
};
const scoreColor = s => s>=80?C.green:s>=60?C.amber:C.red;

function getToken(){ return localStorage.getItem("ic_token"); }
function setToken(t){ localStorage.setItem("ic_token",t); }
function clearToken(){ localStorage.removeItem("ic_token"); }
function authHeaders(){ const t=getToken(); return t?{Authorization:`Bearer ${t}`}:{}; }

function Card({children,style={}}){
  return <div style={{background:C.card,border:`1px solid ${C.border}`,borderRadius:12,padding:"20px 24px",...style}}>{children}</div>;
}
function Label({children}){
  return <p style={{fontSize:11,fontWeight:600,letterSpacing:"0.1em",textTransform:"uppercase",color:C.muted,marginBottom:6}}>{children}</p>;
}
function Tag({children,color=C.muted}){
  return <span style={{display:"inline-block",padding:"2px 10px",borderRadius:99,fontSize:11,fontWeight:600,background:color+"22",color,border:`1px solid ${color}44`,marginRight:6,marginBottom:4}}>{children}</span>;
}
function Spinner({text="Processing…"}){
  return(
    <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:16,padding:"40px 0"}}>
      <div style={{width:40,height:40,border:`3px solid ${C.border}`,borderTop:`3px solid ${C.accent}`,borderRadius:"50%",animation:"spin 0.8s linear infinite"}}/>
      <p style={{color:C.muted,fontSize:13}}>{text}</p>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
function ErrorBox({msg}){
  if(!msg) return null;
  return <div style={{padding:"10px 14px",borderRadius:8,background:C.red+"15",border:`1px solid ${C.red}44`,color:C.red,fontSize:13,marginBottom:14}}>⚠ {msg}</div>;
}
function ProgressBar({value,max,color}){
  return(
    <div style={{background:C.border,borderRadius:99,height:6,overflow:"hidden",flex:1}}>
      <div style={{width:`${(value/max)*100}%`,height:"100%",borderRadius:99,background:color,transition:"width 0.8s ease"}}/>
    </div>
  );
}
function ScoreRing({score}){
  const r=54,circ=2*Math.PI*r,pct=Math.min(Math.max(score,0),100),color=scoreColor(pct);
  return(
    <svg width={128} height={128} viewBox="0 0 128 128">
      <circle cx={64} cy={64} r={r} fill="none" stroke={C.border} strokeWidth={8}/>
      <circle cx={64} cy={64} r={r} fill="none" stroke={color} strokeWidth={8}
        strokeLinecap="round"
        strokeDasharray={`${(pct/100)*circ} ${circ-(pct/100)*circ}`}
        strokeDashoffset={circ/4}/>
      <text x={64} y={58} textAnchor="middle" fill={color} fontSize={26} fontWeight={700} fontFamily="monospace">{score}</text>
      <text x={64} y={76} textAnchor="middle" fill={C.muted} fontSize={11} fontFamily="sans-serif">/ 100</text>
    </svg>
  );
}

// ── Auth ──────────────────────────────────────────────────────────────────────
function AuthScreen({onAuth}){
  const [mode,setMode]=useState("login");
  const [form,setForm]=useState({username:"",email:"",password:"",full_name:""});
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  const set=k=>e=>setForm(f=>({...f,[k]:e.target.value}));
  const submit=async()=>{
    setError("");setLoading(true);
    try{
      const res=await axios.post(`${API}/auth/${mode}`,form);
      if(res.data.success){setToken(res.data.token);onAuth(res.data.user);}
      else setError(res.data.error||"Failed");
    }catch(err){setError(err.response?.data?.error||"Server error");}
    finally{setLoading(false);}
  };
  const inp=(label,key,type="text",ph="")=>(
    <div style={{marginBottom:16}}>
      <p style={{fontSize:11,fontWeight:600,letterSpacing:"0.1em",textTransform:"uppercase",color:C.muted,marginBottom:6}}>{label}</p>
      <input type={type} value={form[key]} onChange={set(key)} placeholder={ph}
        style={{width:"100%",padding:"11px 13px",borderRadius:8,border:`1px solid ${C.border}`,background:C.surface,color:C.text,fontSize:14,outline:"none",boxSizing:"border-box"}}/>
    </div>
  );
  return(
    <div style={{minHeight:"100vh",background:C.bg,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:"'DM Sans','Segoe UI',sans-serif",color:C.text}}>
      <div style={{width:"100%",maxWidth:420,padding:"0 20px"}}>
        <div style={{textAlign:"center",marginBottom:32}}>
          <div style={{width:48,height:48,borderRadius:12,margin:"0 auto 12px",background:`linear-gradient(135deg,${C.accent},${C.teal})`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:20,fontWeight:800,color:"#fff"}}>IC</div>
          <h1 style={{fontSize:22,fontWeight:700,marginBottom:4}}>Intelli-Credit</h1>
          <p style={{fontSize:13,color:C.muted}}>AI-Powered Corporate Credit Engine</p>
        </div>
        <Card>
          <div style={{display:"flex",marginBottom:24,background:C.surface,borderRadius:8,padding:3,gap:3}}>
            {["login","register"].map(m=>(
              <button key={m} onClick={()=>{setMode(m);setError("");}}
                style={{flex:1,padding:"8px",borderRadius:6,border:"none",background:mode===m?C.card:"transparent",color:mode===m?C.text:C.muted,fontSize:13,fontWeight:mode===m?600:400,cursor:"pointer",fontFamily:"inherit",textTransform:"capitalize"}}>
                {m==="login"?"Sign In":"Register"}
              </button>
            ))}
          </div>
          {mode==="register" && inp("Full Name","full_name","text","Your full name")}
          {inp("Username or Email","username","text","username or email")}
          {mode==="register" && inp("Email","email","email","email@yourbank.com")}
          {inp("Password","password","password","Min 8 chars, 1 uppercase, 1 number")}
          <ErrorBox msg={error}/>
          <button onClick={submit} disabled={loading}
            style={{width:"100%",padding:13,borderRadius:8,background:loading?C.muted:`linear-gradient(135deg,${C.accent},${C.teal})`,color:"#fff",fontSize:14,fontWeight:700,border:"none",cursor:loading?"not-allowed":"pointer",fontFamily:"inherit"}}>
            {loading?"Please wait…":mode==="login"?"Sign In":"Create Account"}
          </button>
        </Card>
      </div>
    </div>
  );
}

// ── Upload ────────────────────────────────────────────────────────────────────
function UploadScreen({user,onResult,onLogout}){
  const [company,setCompany]=useState("");
  const [file,setFile]=useState(null);
  const [bankFile,setBankFile]=useState(null);
  const [notes,setNotes]=useState("");
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  const [history,setHistory]=useState([]);

  useEffect(()=>{
    axios.get(`${API}/history`,{headers:authHeaders()}).then(r=>setHistory(r.data)).catch(()=>{});
  },[]);

  const handleSubmit=async()=>{
    setError("");
    if(!company.trim()){setError("Company name is required.");return;}
    if(!file){setError("Please upload an annual report PDF.");return;}
    setLoading(true);
    const fd=new FormData();
    fd.append("file",file);
    fd.append("company_name",company);
    fd.append("officer_notes",notes);
    if(bankFile) fd.append("bank_file",bankFile);
    try{
      const res=await axios.post(`${API}/analyze`,fd,{headers:{"Content-Type":"multipart/form-data",...authHeaders()}});
      onResult(res.data);
    }catch(err){setError(err.response?.data?.error||"Analysis failed. Check backend is running.");}
    finally{setLoading(false);}
  };

  const DropZone=({label,file,onChange,hint})=>(
    <div style={{marginBottom:18}}>
      <p style={{fontSize:11,fontWeight:600,letterSpacing:"0.1em",textTransform:"uppercase",color:C.muted,marginBottom:6}}>{label}</p>
      <label style={{display:"flex",flexDirection:"column",alignItems:"center",padding:"20px",borderRadius:8,border:`2px dashed ${file?C.teal:C.border}`,cursor:"pointer",background:file?C.teal+"10":"transparent"}}>
        <input type="file" accept=".pdf" style={{display:"none"}} onChange={e=>onChange(e.target.files[0])}/>
        <div style={{fontSize:22,marginBottom:6}}>📄</div>
        <p style={{fontSize:13,color:file?C.teal:C.muted,fontWeight:500}}>{file?file.name:"Click to upload PDF"}</p>
        <p style={{fontSize:11,color:C.muted,marginTop:2}}>{hint}</p>
      </label>
    </div>
  );

  return(
    <div style={{minHeight:"100vh",background:C.bg,color:C.text,fontFamily:"'DM Sans','Segoe UI',sans-serif",display:"flex"}}>
      {/* Sidebar */}
      <div style={{width:250,background:C.surface,borderRight:`1px solid ${C.border}`,padding:"28px 18px",display:"flex",flexDirection:"column",gap:24,flexShrink:0}}>
        <div style={{display:"flex",alignItems:"center",gap:10}}>
          <div style={{width:32,height:32,borderRadius:8,background:`linear-gradient(135deg,${C.accent},${C.teal})`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:14,fontWeight:800,color:"#fff"}}>IC</div>
          <div><p style={{fontSize:14,fontWeight:600}}>Intelli-Credit</p><p style={{fontSize:10,color:C.muted}}>v3.1 + ML</p></div>
        </div>
        {user&&(
          <div style={{padding:"10px 12px",borderRadius:8,background:C.card,border:`1px solid ${C.border}`}}>
            <p style={{fontSize:12,fontWeight:600}}>{user.full_name||user.username}</p>
            <p style={{fontSize:11,color:C.muted}}>{user.role}</p>
            <button onClick={onLogout} style={{marginTop:8,fontSize:11,color:C.red,background:"none",border:"none",cursor:"pointer",padding:0,fontFamily:"inherit"}}>Sign out</button>
          </div>
        )}
        <div>
          <p style={{fontSize:11,fontWeight:600,color:C.muted,textTransform:"uppercase",letterSpacing:"0.1em",marginBottom:10}}>Recent Analyses</p>
          {history.length===0
            ?<p style={{fontSize:12,color:C.muted}}>None yet</p>
            :history.slice(0,8).map(h=>(
              <div key={h.id} onClick={async()=>{try{const r=await axios.get(`${API}/history/${h.id}`);onResult(r.data);}catch{}}}
                style={{padding:"9px 11px",borderRadius:7,cursor:"pointer",marginBottom:4,border:`1px solid ${C.border}`,background:C.card}}>
                <p style={{fontSize:12,fontWeight:600,marginBottom:2}}>{h.company_name}</p>
                <p style={{fontSize:10,color:C.muted}}>
                  Score: <span style={{color:scoreColor(h.risk_score)}}>{h.risk_score}</span> · {h.decision}
                </p>
              </div>
            ))
          }
        </div>
      </div>
      {/* Main */}
      <div style={{flex:1,display:"flex",alignItems:"center",justifyContent:"center",padding:40}}>
        <div style={{width:"100%",maxWidth:580}}>
          <h1 style={{fontSize:26,fontWeight:700,marginBottom:6}}>New Credit Analysis</h1>
          <p style={{color:C.muted,marginBottom:28,fontSize:14}}>AI + ML powered credit decision with real-time news research and document intelligence.</p>
          <Card>
            <div style={{marginBottom:18}}>
              <Label>Company Name *</Label>
              <input value={company} onChange={e=>setCompany(e.target.value)} placeholder="e.g. TCS, Infosys, Reliance Industries"
                style={{width:"100%",padding:"11px 13px",borderRadius:8,border:`1px solid ${C.border}`,background:C.surface,color:C.text,fontSize:14,outline:"none",boxSizing:"border-box"}}/>
            </div>
            <DropZone label="Annual Report / Financial Statement *" file={file} onChange={setFile} hint="Annual reports, balance sheets · Max 25 MB"/>
            <DropZone label="Bank Statement (optional — improves ML accuracy)" file={bankFile} onChange={setBankFile} hint="6–12 month bank statement PDF"/>
            <div style={{marginBottom:22}}>
              <Label>Credit Officer Notes (optional)</Label>
              <textarea value={notes} onChange={e=>setNotes(e.target.value)}
                placeholder="e.g. met management on-site, clean repayment history, NCLT case pending..."
                rows={3} style={{width:"100%",padding:"11px 13px",borderRadius:8,border:`1px solid ${C.border}`,background:C.surface,color:C.text,fontSize:14,resize:"vertical",outline:"none",boxSizing:"border-box",fontFamily:"inherit"}}/>
            </div>
            <ErrorBox msg={error}/>
            <button onClick={handleSubmit} disabled={loading}
              style={{width:"100%",padding:13,borderRadius:8,background:loading?C.muted:`linear-gradient(135deg,${C.accent},${C.teal})`,color:"#fff",fontSize:15,fontWeight:700,border:"none",cursor:loading?"not-allowed":"pointer"}}>
              {loading?"Analyzing…":"▶  Run Credit Analysis"}
            </button>
          </Card>
          {loading&&<Spinner text="Running AI + ML analysis pipeline — ~15 seconds…"/>}
        </div>
      </div>
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
function Dashboard({result,onBack}){
  const [tab,setTab]=useState("overview");
  const {company,financials={},research={},analysis={},bank,mca}=result;
  const breakdown=analysis.score_breakdown||{};
  const fiveCs=analysis.five_cs||{};
  const gst=analysis.gst_analysis||{};
  const ml=analysis.ml_analysis||{};
  const score=analysis.risk_score||0;
  const dColor=decisionColor(analysis.decision);

  const breakdownData=[
    {name:"Financial",value:breakdown.financial_score||0,max:40},
    {name:"Leverage", value:breakdown.leverage_score||0, max:20},
    {name:"External", value:breakdown.external_score||0, max:20},
    {name:"GST",      value:breakdown.gst_score||0,      max:10},
    {name:"Officer",  value:breakdown.qualitative_score||0,max:10},
  ];

  const TABS=["overview","ml-model","bank","mca","research","five-cs","narrative"];

  return(
    <div style={{minHeight:"100vh",background:C.bg,color:C.text,fontFamily:"'DM Sans','Segoe UI',sans-serif"}}>
      {/* Nav */}
      <div style={{background:C.surface,borderBottom:`1px solid ${C.border}`,padding:"0 28px",display:"flex",alignItems:"center",justifyContent:"space-between",height:56}}>
        <div style={{display:"flex",alignItems:"center",gap:14}}>
          <div style={{width:30,height:30,borderRadius:7,background:`linear-gradient(135deg,${C.accent},${C.teal})`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:13,fontWeight:800,color:"#fff"}}>IC</div>
          <span style={{fontSize:13,fontWeight:600}}>Intelli-Credit</span>
          <span style={{color:C.border}}>›</span>
          <span style={{fontSize:13,color:C.muted}}>{company}</span>
        </div>
        <button onClick={onBack} style={{padding:"6px 14px",borderRadius:7,border:`1px solid ${C.border}`,background:"transparent",color:C.subtle,cursor:"pointer",fontSize:12}}>+ New Analysis</button>
      </div>

      <div style={{maxWidth:1100,margin:"0 auto",padding:"28px 20px"}}>
        {/* Hero */}
        <div style={{display:"grid",gridTemplateColumns:"auto 1fr auto",gap:22,alignItems:"center",marginBottom:24}}>
          <ScoreRing score={score}/>
          <div>
            <h2 style={{fontSize:24,fontWeight:700,marginBottom:4}}>{company}</h2>
            {mca&&mca.status&&mca.status!=="Not retrieved"&&(
              <p style={{fontSize:12,color:C.muted,marginBottom:6}}>
                MCA: <span style={{color:mca.status.toLowerCase().includes("active")?C.green:C.amber}}>{mca.status}</span>
                {mca.company_type&&` · ${mca.company_type}`}
              </p>
            )}
            <p style={{color:C.muted,fontSize:13,marginBottom:10}}>
              {research.articles_analyzed||0} articles · Sentiment: <span style={{color:score>=70?C.green:score>=55?C.amber:C.red}}>{research.overall_sentiment||"Neutral"}</span>
              {ml&&ml.ml_grade&&<span> · <span style={{color:C.purple}}>{ml.ml_grade}</span></span>}
            </p>
            <div>
              <Tag color={dColor}>{analysis.decision}</Tag>
              <Tag color={C.accent}>{analysis.interest_rate}</Tag>
              {ml.ml_reject_probability!=null&&(
                <Tag color={ml.ml_reject_probability<0.3?C.green:ml.ml_reject_probability<0.6?C.amber:C.red}>
                  ML Reject Risk: {(ml.ml_reject_probability*100).toFixed(0)}%
                </Tag>
              )}
            </div>
          </div>
          <Card style={{textAlign:"center",minWidth:170}}>
            <Label>Indicative Loan</Label>
            <p style={{fontSize:17,fontWeight:700,color:dColor,lineHeight:1.3}}>{analysis.loan_amount||"N/A"}</p>
          </Card>
        </div>

        {/* Metrics */}
        <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12,marginBottom:20}}>
          {[
            {label:"Revenue",val:financials.revenue_display||"N/A",color:C.text},
            {label:"Net Profit/PAT",val:financials.profit_display||"N/A",color:parseFloat(financials.profit)>0?C.green:C.red},
            {label:"Total Debt",val:financials.debt_display||"N/A",color:C.amber},
            {label:"GST Status",val:gst.gst_risk_level||"N/A",color:(gst.gst_penalty||0)===0?C.green:C.amber},
          ].map(({label,val,color})=>(
            <Card key={label}><Label>{label}</Label><p style={{fontSize:15,fontWeight:700,color}}>{val}</p></Card>
          ))}
        </div>

        {/* Score breakdown */}
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:18,marginBottom:22}}>
          <Card>
            <Label>Score breakdown</Label>
            {breakdownData.map(({name,value,max})=>{
              const color=value/max>=0.75?C.green:value/max>=0.5?C.amber:C.red;
              return(
                <div key={name} style={{display:"flex",alignItems:"center",gap:10,marginBottom:10}}>
                  <span style={{fontSize:12,color:C.subtle,width:64}}>{name}</span>
                  <ProgressBar value={value} max={max} color={color}/>
                  <span style={{fontSize:12,fontWeight:600,color,width:28,textAlign:"right"}}>{value}</span>
                </div>
              );
            })}
          </Card>
          <Card>
            <Label>Radar view</Label>
            <ResponsiveContainer width="100%" height={190}>
              <RadarChart data={breakdownData.map(d=>({subject:d.name,score:Math.round((d.value/d.max)*100)}))}>
                <PolarGrid stroke={C.border}/>
                <PolarAngleAxis dataKey="subject" tick={{fill:C.muted,fontSize:11}}/>
                <Radar dataKey="score" stroke={C.accent} fill={C.accent} fillOpacity={0.25} strokeWidth={2}/>
              </RadarChart>
            </ResponsiveContainer>
          </Card>
        </div>

        {/* Tabs */}
        <div style={{display:"flex",gap:2,borderBottom:`1px solid ${C.border}`,marginBottom:18}}>
          {TABS.map(t=>(
            <button key={t} onClick={()=>setTab(t)}
              style={{padding:"9px 14px",fontSize:12,background:"transparent",border:"none",cursor:"pointer",fontFamily:"inherit",color:tab===t?C.accent:C.muted,borderBottom:`2px solid ${tab===t?C.accent:"transparent"}`,textTransform:"capitalize"}}>
              {t.replace("-"," ")}
            </button>
          ))}
        </div>

        {/* Tab: Overview */}
        {tab==="overview"&&(
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:18}}>
            <Card><Label>Decision explanation</Label>
              <p style={{fontSize:13,color:C.subtle,lineHeight:1.7}}>{analysis.explanation}</p>
            </Card>
            <Card><Label>Risk flags ({(analysis.risk_flags||[]).length})</Label>
              {(analysis.risk_flags||[]).length===0
                ?<p style={{color:C.green,fontSize:13}}>✓ No significant risk flags</p>
                :(analysis.risk_flags||[]).map((f,i)=>(
                  <div key={i} style={{padding:"7px 10px",borderRadius:6,background:C.red+"12",border:`1px solid ${C.red}22`,marginBottom:6,fontSize:12,color:C.red}}>⚠ {f}</div>
                ))
              }
            </Card>
          </div>
        )}

        {/* Tab: ML Model */}
        {tab==="ml-model"&&(
          <div>
            {ml.error&&!ml.ml_grade
              ?<Card><p style={{color:C.amber,fontSize:13}}>ML model not available: {ml.error}</p></Card>
              :<>
                <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:14,marginBottom:18}}>
                  <Card style={{textAlign:"center"}}>
                    <Label>ML Reject Probability</Label>
                    <p style={{fontSize:26,fontWeight:700,color:ml.ml_reject_probability<0.3?C.green:ml.ml_reject_probability<0.6?C.amber:C.red}}>
                      {((ml.ml_reject_probability||0)*100).toFixed(1)}%
                    </p>
                  </Card>
                  <Card style={{textAlign:"center"}}>
                    <Label>ML Prediction</Label>
                    <p style={{fontSize:18,fontWeight:700,color:ml.ml_prediction==="Approve"?C.green:C.red}}>{ml.ml_prediction}</p>
                  </Card>
                  <Card style={{textAlign:"center"}}>
                    <Label>Score Adjustment</Label>
                    <p style={{fontSize:22,fontWeight:700,color:ml.ml_score_adjustment>=0?C.green:C.red}}>
                      {ml.ml_score_adjustment>=0?"+":""}{ml.ml_score_adjustment} pts
                    </p>
                  </Card>
                </div>
                <Card>
                  <Label>ML feature inputs — {ml.ml_grade}</Label>
                  <p style={{fontSize:12,color:C.muted,marginBottom:14}}>GradientBoostingClassifier trained on 2,000 synthetic credit profiles. Features used:</p>
                  {Object.entries(ml.ml_features||{}).map(([k,v])=>(
                    <div key={k} style={{display:"flex",gap:16,padding:"7px 0",borderBottom:`1px solid ${C.border}`}}>
                      <span style={{fontSize:12,color:C.muted,width:200,flexShrink:0}}>{k.replace(/_/g," ")}</span>
                      <span style={{fontSize:13,fontWeight:500,color:C.text}}>{typeof v==="number"?v.toFixed(3):v}</span>
                    </div>
                  ))}
                </Card>
              </>
            }
          </div>
        )}

        {/* Tab: Bank */}
        {tab==="bank"&&(
          <div>
            {!bank||bank.error
              ?<Card><p style={{color:C.muted,fontSize:14}}>{bank?.error||"No bank statement uploaded."}</p></Card>
              :<>
                <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:14,marginBottom:18}}>
                  {[
                    {label:"Avg Monthly Balance",val:bank.avg_monthly_balance_display,color:C.text},
                    {label:"Inflow/Outflow Ratio",val:bank.inflow_outflow_ratio+"x",color:bank.inflow_outflow_ratio>=1.2?C.green:C.amber},
                    {label:"Bounce Count",val:bank.bounce_count,color:bank.bounce_count===0?C.green:bank.bounce_count<=2?C.amber:C.red},
                    {label:"Total Credits",val:bank.total_credits_display,color:C.green},
                    {label:"Total Debits",val:bank.total_debits_display,color:C.red},
                    {label:"OD Utilisation",val:bank.od_utilisation_pct+"%",color:bank.od_utilisation_pct>70?C.red:C.green},
                  ].map(({label,val,color})=>(
                    <Card key={label}><Label>{label}</Label><p style={{fontSize:16,fontWeight:700,color}}>{val}</p></Card>
                  ))}
                </div>
                <Card>
                  <Label>Bank flags & signals</Label>
                  {bank.bank_flags.length===0?<p style={{color:C.green,fontSize:13}}>✓ No banking risk flags</p>
                    :bank.bank_flags.map((f,i)=><div key={i} style={{padding:"7px 10px",borderRadius:6,background:C.red+"12",border:`1px solid ${C.red}22`,marginBottom:6,fontSize:12,color:C.red}}>⚠ {f}</div>)}
                  {bank.bank_positive.map((p,i)=><div key={i} style={{padding:"7px 10px",borderRadius:6,background:C.green+"12",marginBottom:6,fontSize:12,color:C.green}}>✓ {p}</div>)}
                </Card>
              </>
            }
          </div>
        )}

        {/* Tab: MCA */}
        {tab==="mca"&&(
          <Card>
            <Label>MCA / ROC company data</Label>
            {!mca?<p style={{color:C.muted,fontSize:13}}>MCA lookup not performed</p>
              :<div>
                {[["CIN",mca.cin],["Company Type",mca.company_type],["Status",mca.status],["ROC",mca.roc],["Date of Incorporation",mca.date_incorporation],["Paid-up Capital",mca.paid_up_capital],["Registered State",mca.registered_state],["Data Source",mca.source]].map(([k,v])=>(
                  <div key={k} style={{display:"flex",gap:16,padding:"8px 0",borderBottom:`1px solid ${C.border}`}}>
                    <span style={{fontSize:12,color:C.muted,width:170,flexShrink:0}}>{k}</span>
                    <span style={{fontSize:13,color:k==="Status"&&(v||"").toLowerCase().includes("active")?C.green:C.text}}>{v||"N/A"}</span>
                  </div>
                ))}
                {(mca.mca_flags||[]).map((f,i)=><div key={i} style={{padding:"7px 10px",borderRadius:6,background:C.red+"12",border:`1px solid ${C.red}22`,marginBottom:6,fontSize:12,color:C.red,marginTop:12}}>⚠ {f}</div>)}
                {mca.error&&<p style={{fontSize:12,color:C.amber,marginTop:10}}>Note: {mca.error}</p>}
              </div>
            }
          </Card>
        )}

        {/* Tab: Research */}
        {tab==="research"&&(
          <div>
            <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:14,marginBottom:18}}>
              {[
                {label:"Critical Alerts",val:research.severity_counts?.critical||0,color:C.red},
                {label:"High Risk Signals",val:research.severity_counts?.high||0,color:C.amber},
                {label:"Positive News",val:(research.positive_signals||[]).length,color:C.green},
              ].map(({label,val,color})=>(
                <Card key={label} style={{textAlign:"center"}}><Label>{label}</Label><p style={{fontSize:28,fontWeight:700,color}}>{val}</p></Card>
              ))}
            </div>
            <Card>
              <Label>News articles scanned ({(research.news_details||[]).length})</Label>
              {(research.news_details||[]).length===0?<p style={{color:C.muted,fontSize:13}}>No articles found</p>
                :(research.news_details||[]).map((a,i)=>{
                  const sc=a.severity==="critical"?C.red:a.severity==="high"?C.amber:a.severity==="positive"?C.green:C.muted;
                  return(
                    <div key={i} style={{padding:"9px 12px",borderRadius:8,border:`1px solid ${C.border}`,marginBottom:8,display:"flex",gap:12,alignItems:"flex-start"}}>
                      <span style={{fontSize:10,fontWeight:700,color:sc,textTransform:"uppercase",marginTop:2,width:52,flexShrink:0}}>{a.severity||"neutral"}</span>
                      <div>
                        <p style={{fontSize:13,color:C.text,lineHeight:1.4}}>{a.title}</p>
                        <p style={{fontSize:11,color:C.muted,marginTop:2}}>{a.source} · {a.pub_date}</p>
                      </div>
                    </div>
                  );
                })
              }
            </Card>
          </div>
        )}

        {/* Tab: Five Cs */}
        {tab==="five-cs"&&(
          <div style={{display:"grid",gap:12}}>
            {[{key:"character",label:"Character",icon:"👤"},{key:"capacity",label:"Capacity",icon:"⚡"},{key:"capital",label:"Capital",icon:"🏦"},{key:"collateral",label:"Collateral",icon:"🏛"},{key:"conditions",label:"Conditions",icon:"🌐"}].map(({key,label,icon})=>(
              <Card key={key} style={{display:"flex",gap:18,alignItems:"flex-start"}}>
                <div style={{fontSize:22,width:36,flexShrink:0}}>{icon}</div>
                <div><p style={{fontSize:13,fontWeight:700,marginBottom:5}}>{label}</p>
                  <p style={{fontSize:13,color:C.subtle,lineHeight:1.7}}>{fiveCs[key]||"Not assessed"}</p>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Tab: Narrative */}
        {tab==="narrative"&&(
          <Card>
            <Label>Detailed risk narrative</Label>
            {(analysis.detailed_narrative||[]).length===0
              ?<p style={{color:C.green,fontSize:13}}>No risk observations.</p>
              :(analysis.detailed_narrative||[]).map((item,i)=>(
                <div key={i} style={{display:"flex",gap:12,marginBottom:10,padding:"9px 12px",borderRadius:7,background:i%2===0?C.surface:"transparent"}}>
                  <span style={{color:C.accent,fontSize:15,marginTop:1}}>→</span>
                  <p style={{fontSize:13,color:C.subtle,lineHeight:1.7}}>{item}</p>
                </div>
              ))
            }
          </Card>
        )}

        {/* Download */}
        {result.cam_report&&(
          <div style={{marginTop:22,display:"flex",justifyContent:"flex-end"}}>
            <a href={`${API}/download/${result.cam_report}`} target="_blank" rel="noreferrer"
              style={{padding:"11px 26px",borderRadius:8,background:`linear-gradient(135deg,${C.teal},${C.accent})`,color:"#fff",textDecoration:"none",fontSize:14,fontWeight:700}}>
              ↓ Download CAM Report PDF
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

// ── App root ──────────────────────────────────────────────────────────────────
export default function App(){
  const [user,setUser]=useState(null);
  const [result,setResult]=useState(null);
  const [checking,setChecking]=useState(true);

  useEffect(()=>{
    const token=getToken();
    if(!token){setChecking(false);return;}
    axios.get(`${API}/auth/me`,{headers:authHeaders()})
      .then(r=>setUser(r.data.user))
      .catch(()=>clearToken())
      .finally(()=>setChecking(false));
  },[]);

  if(checking) return(
    <div style={{minHeight:"100vh",background:"#0a0f1e",display:"flex",alignItems:"center",justifyContent:"center"}}>
      <Spinner text="Loading…"/>
    </div>
  );
  if(!user) return <AuthScreen onAuth={u=>setUser(u)}/>;
  if(result) return <Dashboard result={result} onBack={()=>setResult(null)}/>;
  return <UploadScreen user={user} onResult={setResult} onLogout={()=>{clearToken();setUser(null);}}/>;
}
