// Final scoped product QA. Disposable demo_product.py --start :8770; Vite :5178.
async(page)=>{
  // Localhost cookies span ports. Isolate from previous phase QA tabs.
  const context=await page.context().browser().newContext()
  page=await context.newPage()
  const base='http://127.0.0.1:8770',results=[],errors=[]
  const check=(ok,message)=>{if(!ok)throw Error(message)}
  page.on('pageerror',e=>errors.push(e.message))
  const login=async username=>{
    await page.goto('http://127.0.0.1:5178')
    await page.evaluate(async({base,username})=>{
      const s=await fetch(base+'/auth/session',{credentials:'include'}).then(r=>r.json())
      const r=await fetch(base+'/auth/login',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json','X-CSRF-Token':s.csrf_token},body:JSON.stringify({username,password:'Synthetic-demo-only-2026'})})
      if(!r.ok)throw Error('Synthetic login failed')
    },{base,username})
    await page.reload();await page.locator('main h1').waitFor()
    await page.waitForFunction(()=>!(/Opening|Loading your|could not|can’t open/i.test(document.querySelector('main')?.innerText||'')))
    if(['demo-admin','demo-presenter'].includes(username))await page.getByRole('navigation',{name:'Administration navigation',exact:true}).waitFor()
    else if(username==='demo-owner')await page.getByRole('heading',{name:'Appoint an administrator',exact:true}).waitFor()
    else if(username==='demo-manager')await page.locator('.manager-command-heading h1').waitFor()
    else if(username.startsWith('demo-resident'))await page.getByRole('heading',{name:/Welcome home/}).waitFor()
    else await page.getByRole('heading',{name:'Business X',exact:true}).waitFor()
  }
  const roles=[
    ['demo-owner','Administration navigation',['Setup','Roles & Permissions']],
    ['demo-admin','Administration navigation',['Setup','Building','Hardware','Integrations','Accounts','Roles & Permissions','Policies','System & Audit']],
    ['demo-manager','Manager navigation',['Overview','People','Visitors','Access','Maintenance','Security','Activity','Announcements']],
    ['demo-resident','Resident navigation',['Home','Visitors','Maintenance','Access','Notices']],
    ['demo-business','Business navigation',['Home','Visitors','Staff','Maintenance','Access','Notices','My Business']],
    ['demo-staff','Business navigation',['Home','Visitors','Maintenance','Access','Notices']],
  ]
  for(const [username,navName,names] of roles){
    await page.setViewportSize({width:1440,height:900})
    await login(username)
    const nav=page.getByRole('navigation',{name:navName})
    check(await nav.getByRole('button').count()===names.length,'Wrong role navigation: '+username)
    check(await page.getByLabel('Switch workspace',{exact:true}).count()===0,'Single role needs no selector')
    if(username!=='demo-manager')check(await page.getByRole('button',{name:'Demo Mode',exact:true}).count()===0,'Simulation advertised to tenant/config-only role')
    for(const width of [1440,768,390]){
      await page.setViewportSize({width,height:900})
      for(const name of names){
        if(username==='demo-resident'&&width===390&&name==='Notices'){
          check(await nav.getByRole('button',{name:'Notices',exact:true}).count()===0,'Notices should stay in Home and its archive on mobile')
          await nav.getByRole('button',{name:'Home',exact:true}).click()
          await page.getByRole('button',{name:'All notices',exact:true}).click()
          check(await page.locator('main').getAttribute('data-page')==='Notices','Resident notice archive is not reachable from Home')
          continue
        }
        if(navName==='Manager navigation'&&width<1200)await page.getByLabel('Manager section',{exact:true}).selectOption(name)
        else await nav.getByRole('button',{name,exact:true}).click()
        check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Overflow '+username+' '+name+' '+width)
        check(await page.locator('button').evaluateAll(els=>els.every(e=>{const r=e.getBoundingClientRect();return r.height===0||r.height>=44})),'Small button '+username+' '+name)
        await page.evaluate(()=>window.scrollTo(0,0))
        if(username==='demo-resident')check(!(await page.locator('main').innerText()).includes('Business X reception update'),'Residential notice leak')
        if(username.startsWith('demo-business')||username==='demo-staff')check(!(await page.locator('main').innerText()).includes('Water inspection tomorrow'),'Business notice leak')
        if(name===names[0])await page.screenshot({path:`C:/dev/nodum/docs/qa/g-${username}-${width}.png`,fullPage:true})
        results.push(`${username} ${name} ${width}`)
      }
      await page.locator('.skip-link').focus();await page.keyboard.press('Enter')
      check(await page.evaluate(()=>document.activeElement.tagName==='MAIN'),'Skip link failed '+username)
      if(navName==='Manager navigation'&&width<1200)await page.getByLabel('Manager section',{exact:true}).focus()
      else await nav.getByRole('button').first().focus()
      check(await page.evaluate(()=>getComputedStyle(document.activeElement).outlineStyle!=='none'),'No visible keyboard focus')
    }
  }
  await login('demo-presenter');await page.setViewportSize({width:390,height:900})
  const switcher=page.getByLabel('Switch workspace',{exact:true})
  const identity=await page.evaluate(async base=>(await fetch(base+'/auth/session',{credentials:'include'}).then(r=>r.json())).user.id,base)
  await switcher.selectOption('Resident')
  await page.getByRole('heading',{name:/Welcome/}).waitFor()
  await page.getByRole('navigation',{name:'Resident navigation'}).getByRole('button',{name:'Visitors',exact:true}).click()
  await page.getByRole('button',{name:'Invite visitor',exact:true}).click()
  const visitor='Demo cousin '+Date.now()
  await page.getByLabel('Visitor name',{exact:true}).fill(visitor)
  const times=await page.evaluate(()=>{const local=d=>new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);return [local(new Date(Date.now()-60000)),local(new Date(Date.now()+7200000))]})
  await page.getByLabel('Arrival window starts').fill(times[0])
  await page.getByLabel('Arrival window ends').fill(times[1])
  await page.getByRole('button',{name:'Schedule visitor',exact:true}).click()
  const pass=page.getByLabel('Visitor pass record')
  await pass.waitFor()
  check(await pass.getByRole('heading',{name:visitor,exact:true}).count()===1,'Visitor pass does not show the created visitor')
  check(/No scannable visitor credential is issued/i.test(await pass.innerText()),'Pass implies a usable QR credential')
  check(/does not unlock a door/i.test(await pass.innerText()),'Pass implies physical access')
  await pass.getByRole('button',{name:'Close pass',exact:true}).click()
  await page.locator('.resident-record').filter({has:page.getByRole('heading',{name:visitor,exact:true})}).getByRole('button',{name:'View pass',exact:true}).click()
  await pass.waitFor()
  await page.reload()
  await page.getByLabel('Switch workspace',{exact:true}).selectOption('Resident')
  await page.getByRole('navigation',{name:'Resident navigation'}).getByRole('button',{name:'Visitors',exact:true}).click()
  await page.locator('.resident-record').filter({has:page.getByRole('heading',{name:visitor,exact:true})}).getByRole('button',{name:'View pass',exact:true}).click()
  await pass.waitFor()
  check((await pass.innerText()).includes(visitor),'Pass could not reopen after refresh')
  await page.screenshot({path:'C:/dev/nodum/docs/qa/g-resident-visitor-pass-390.png',fullPage:true})
  await page.getByRole('button',{name:'Demo Mode',exact:true}).click()
  await page.getByRole('region',{name:'Ring demo controls'}).getByRole('button',{name:'Visitor arrives',exact:true}).click()
  await page.getByText(/3 signed simulation events received and persisted/).waitFor()
  await page.getByRole('button',{name:'Demo Mode',exact:true}).click()
  await switcher.selectOption('Manager')
  await page.getByLabel('Manager section',{exact:true}).selectOption('Visitors')
  await page.getByRole('heading',{name:visitor,exact:true}).waitFor()
  check(/identity.*not established|identity.*unverified|does not establish visitor identity|do not identify visitors/i.test(await page.locator('main').innerText()),'Missing Ring identity boundary')
  const record=page.getByRole('article').filter({has:page.getByRole('heading',{name:visitor,exact:true})})
  await record.getByText(/^expected$/i).waitFor()
  await page.screenshot({path:'C:/dev/nodum/docs/qa/g-ring-review-390.png',fullPage:true})
  await record.getByRole('button',{name:'Mark arrived',exact:true}).click()
  await record.getByText(/^arrived$/i).waitFor()
  await page.getByLabel('Manager section',{exact:true}).selectOption('Activity')
  await page.getByText('Visitor arrival signal',{exact:true}).first().waitFor()
  check((await page.locator('main').innerText()).includes('Main entrance zone'),'Missing configured event location')
  await page.screenshot({path:'C:/dev/nodum/docs/qa/g-activity-390.png',fullPage:true})
  await switcher.selectOption('Business')
  await page.getByRole('heading',{name:'Business X',exact:true}).waitFor()
  check((await page.locator('.business-no-signal').innerText()).includes('No recent Ring arrival signals in this business scope.'),'Shared-entrance Ring signal leaked into an unmapped business scope')
  await switcher.selectOption('Resident')
  check(await page.getByRole('navigation',{name:'Manager navigation'}).count()===0,'Operator state retained after switch')
  const after=await page.evaluate(async base=>(await fetch(base+'/auth/session',{credentials:'include'}).then(r=>r.json())).user.id,base)
  check(identity===after,'Workspace selection changed identity')
  // A genuinely authorized Admin changes its own Resident affiliation in this
  // disposable multi-role fixture. Session marker must clear stale unit data.
  const membership=await page.evaluate(async({base,identity})=>{
    const rows=await fetch(base+'/structure/affiliations',{credentials:'include'}).then(r=>r.json())
    const a=rows.find(a=>a.user_id===identity&&a.role==='resident')
    if(!a)throw Error('Missing own synthetic membership')
    const s=await fetch(base+'/auth/session',{credentials:'include'}).then(r=>r.json())
    const r=await fetch(base+'/admin/affiliations/'+encodeURIComponent(a.id),{method:'PUT',credentials:'include',headers:{'Content-Type':'application/json','X-CSRF-Token':s.csrf_token},body:JSON.stringify({...a,active:false})})
    if(!r.ok)throw Error('Authorized membership revocation failed')
    window.dispatchEvent(new Event('nodum:session-check'))
    return {affiliation:a,version:s.authorization.context_version}
  },{base,identity})
  await page.waitForFunction(version=>document.querySelector('.product-bar')?.getAttribute('data-session-version')!==version,membership.version)
  await page.waitForFunction(()=>!document.querySelector('main')?.innerText.includes('Apartment 101'))
  await page.evaluate(async({base,membership})=>{
    const s=await fetch(base+'/auth/session',{credentials:'include'}).then(r=>r.json())
    const r=await fetch(base+'/admin/affiliations/'+encodeURIComponent(membership.affiliation.id),{method:'PUT',credentials:'include',headers:{'Content-Type':'application/json','X-CSRF-Token':s.csrf_token},body:JSON.stringify(membership.affiliation)})
    if(!r.ok)throw Error('Membership recovery failed')
    window.dispatchEvent(new Event('nodum:session-check'))
  },{base,membership})
  await page.waitForFunction(version=>document.querySelector('.product-bar')?.getAttribute('data-session-version')===version,membership.version)
  await page.getByRole('heading',{name:/Welcome home/}).waitFor()
  await page.getByRole('navigation',{name:'Resident navigation'}).getByRole('button',{name:'Visitors',exact:true}).click()
  await page.getByRole('heading',{name:visitor,exact:true}).waitFor()
  // Fail closed on session loss; no private record remains in the document.
  await page.route(base+'/resident/snapshot',route=>route.fulfill({status:401,contentType:'application/json',body:JSON.stringify({detail:'Sign in'})}))
  await page.getByRole('button',{name:'Refresh your information'}).click()
  await page.getByRole('heading',{name:'Welcome to Nodum',exact:true}).waitFor()
  check(!(await page.locator('body').innerText()).includes(visitor),'Stale private visitor after 401')
  await page.unroute(base+'/resident/snapshot')
  await login('demo-staff')
  await page.getByRole('button',{name:'Ask Nodum',exact:true}).click()
  check(await page.locator('.nodum-assistant-panel').evaluate(e=>document.activeElement===e&&e.getBoundingClientRect().top>=0&&e.getBoundingClientRect().top<innerHeight),'Assistant did not reveal and receive focus')
  await page.keyboard.press('Escape')
  check(await page.getByRole('button',{name:'Ask Nodum',exact:true}).evaluate(e=>document.activeElement===e),'Assistant did not return focus')
  await page.getByRole('button',{name:'Ask Nodum',exact:true}).click()
  check((await page.locator('main').innerText()).includes('Guide'),'Local Guide missing')
  await page.getByLabel('Your question',{exact:true}).fill('Who is coming this afternoon?')
  await page.getByRole('region',{name:'Ask Nodum and Business Guide',exact:true}).getByRole('button',{name:'Ask Nodum',exact:true}).click()
  await page.getByText('AI unavailable · Use local Guide',{exact:true}).waitFor()
  // Network failure and recovery clear private projections.
  await page.route(base+'/business-workspace/snapshot',route=>route.abort())
  await page.getByRole('button',{name:'Refresh business information'}).click()
  await page.getByRole('heading',{name:'We can’t open your business right now',exact:true}).waitFor()
  await page.unroute(base+'/business-workspace/snapshot')
  await page.getByRole('button',{name:'Try again',exact:true}).click()
  await page.getByRole('heading',{name:'Business X',exact:true}).waitFor()
  await page.getByRole('button',{name:'Sign out',exact:true}).click()
  await page.getByRole('heading',{name:'Welcome to Nodum',exact:true}).waitFor()
  check(errors.length===0,'Uncaught exceptions: '+errors.join(';'))
  await context.close()
  return {matrix:results.length,results,hero:'Signed arrival, manual identity review/arrival, scoped Activity, no identity switch',session:'Affiliation revocation/recovery, 401 clearing, logout clearing',outage:'Guide and backend error recovery',errors}
}
