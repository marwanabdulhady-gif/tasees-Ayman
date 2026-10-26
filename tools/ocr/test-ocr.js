const { createWorker } = require('tesseract.js');
const path = require('path');
(async()=>{
  const langPath = path.resolve(__dirname,'lang-data');
  const cachePath = path.resolve(__dirname,'.cache');
  const w = await createWorker('ara', 1, { langPath, cachePath, gzip:true, logger:m=>{ if(m.status==='recognizing text') process.stdout.write('.'); } });
  for (const f of ['test-256.png','test-18.png','test-150.png']) {
    const file = path.resolve(__dirname,'../../.cache/ocr',f);
    const t0=Date.now();
    const { data } = await w.recognize(file, { preserve_interword_spaces:'1' }, { text:true, blocks:true } );
    console.log('\n==== '+f+' ('+(Date.now()-t0)+'ms) ====');
    console.log(data.text.slice(0,1400));
  }
  await w.terminate();
})().catch(e=>{console.error(e);process.exit(1)});
