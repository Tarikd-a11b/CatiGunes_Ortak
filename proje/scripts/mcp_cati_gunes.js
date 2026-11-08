#!/usr/bin/env node
// Claude Desktop icin Cati GES projesi kopru sunucusu (MCP, stdio). SALT OKUNUR, bagimliliksiz.
// Yalniz asagidaki 3 not ile 2 proje klasorunu gorur; kasanin geri kalanina erisemez.
// Kurulum: claude_desktop_config.json > mcpServers > "cati-gunes" (node + bu dosyanin yolu).
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const HOME = process.env.USERPROFILE || 'C:\\Users\\dmrta';
const KASA = path.join(HOME, 'Desktop', 'Obsidian', 'Tarik21', 'wiki', 'projeler');

const NOTLAR = {
  'notlar/guncel-durum.md': path.join(HOME, '.claude', 'projects', 'C--Users-dmrta', 'memory', 'project_cati_gunes_paneli.md'),
  'notlar/calisma-gunlugu.md': path.join(KASA, 'cati-gunes-calisma-gunlugu.md'),
  'notlar/kaynak-analizi.md': path.join(KASA, 'cati-gunes-kaynak-analizi.md'),
};
const KLASORLER = {
  proje: path.join(HOME, 'Desktop', 'Projeler', 'CatiGunes'),
  model: path.join(HOME, 'Desktop', 'CatiGunes_Model_Verisi'),
};
const ARAMA_KLASORLERI = ['proje/scripts', 'proje/rapor', 'proje/veri/README.md', 'model/BENIOKU.md', 'model/DOGRULAMA_RAPORU.md'];

const METIN = new Set(['.md', '.txt', '.csv', '.json', '.py', '.js', '.html', '.geojson', '.tsv', '.yaml', '.yml']);
const YASAK_AD = /(key|secret|token|credential|password|anahtar|sifre|şifre)/i;
const ARAMA_UZANTI = new Set(['.md', '.txt', '.py', '.json']);
const AZAMI_DOSYA = 30 * 1024 * 1024;
const AZAMI_CIKTI = 60000;

function yolCoz(sanal) {
  const temiz = String(sanal || '').replace(/\\/g, '/').replace(/^\/+|\/+$/g, '');
  if (NOTLAR[temiz]) return NOTLAR[temiz];
  const parcalar = temiz.split('/').filter(Boolean);
  if (parcalar.includes('..')) throw new Error('Bu yola erişim yok.');
  const kok = KLASORLER[parcalar[0]];
  if (!kok) throw new Error(`Bilinmeyen yol: "${temiz}". dosya_listele ile başla.`);
  for (const p of parcalar.slice(1)) {
    if (p.startsWith('.') || YASAK_AD.test(p)) throw new Error('Bu dosya gizli/hassas sayıldığı için kapalı.');
  }
  const hedef = path.resolve(kok, ...parcalar.slice(1));
  // Sembolik baglanti/junction ile kok disina cikmayi gercek yolla engelle.
  const gercekKok = fs.realpathSync(kok);
  const gercek = fs.realpathSync(hedef);
  const fark = path.relative(gercekKok, gercek);
  if (fark.startsWith('..') || path.isAbsolute(fark)) throw new Error('Bu yola erişim yok.');
  return gercek;
}

function metinOku(gercek) {
  const bilgi = fs.statSync(gercek);
  if (!bilgi.isFile()) throw new Error('Bu bir dosya değil; dosya_listele kullan.');
  if (!METIN.has(path.extname(gercek).toLowerCase())) {
    throw new Error(`Yalnız metin dosyaları okunur (${[...METIN].join(' ')}). PDF/DOCX için dosyayı sohbete yükle.`);
  }
  if (bilgi.size > AZAMI_DOSYA) throw new Error('Dosya 30 MB üstünde, okunmuyor.');
  return fs.readFileSync(gercek, 'utf8').replace(/^\uFEFF/, '');
}

function dosyaListele({ yol } = {}) {
  const temiz = String(yol || '').replace(/\\/g, '/').replace(/^\/+|\/+$/g, '');
  if (!temiz) {
    return ['notlar/  (önce notlar/guncel-durum.md oku)', ...Object.keys(NOTLAR).map((n) => '  ' + n),
      'proje/  (CatiGunes kod + veri)', 'model/  (CatiGunes_Model_Verisi; ana tablo master_veriseti.csv)'].join('\n');
  }
  if (temiz === 'notlar') return Object.keys(NOTLAR).join('\n');
  const gercek = yolCoz(temiz);
  const girdiler = fs.readdirSync(gercek, { withFileTypes: true })
    .filter((g) => !g.name.startsWith('.') && !YASAK_AD.test(g.name));
  const satirlar = girdiler.slice(0, 500).map((g) => {
    if (g.isDirectory()) return `${temiz}/${g.name}/`;
    const kb = Math.ceil(fs.statSync(path.join(gercek, g.name)).size / 1024);
    return `${temiz}/${g.name}  (${kb} KB)`;
  });
  if (girdiler.length > 500) satirlar.push(`... ${girdiler.length - 500} girdi daha`);
  return satirlar.join('\n') || '(boş)';
}

function dosyaOku({ yol, baslangic = 1, satir_sayisi = 300 } = {}) {
  const satirlar = metinOku(yolCoz(yol)).split(/\r?\n/);
  const bas = Math.max(1, Math.floor(baslangic));
  const adet = Math.min(1000, Math.max(1, Math.floor(satir_sayisi)));
  let cikti = '';
  let son = bas - 1;
  for (let i = bas - 1; i < Math.min(satirlar.length, bas - 1 + adet); i++) {
    const s = `${i + 1}\t${satirlar[i]}\n`;
    if (cikti.length + s.length > AZAMI_CIKTI && cikti) break;
    cikti += s;
    son = i + 1;
  }
  const dipnot = son < satirlar.length
    ? `\n[${bas}-${son}. satırlar, toplam ${satirlar.length}. Devamı için baslangic=${son + 1}]`
    : `\n[Dosya sonu, toplam ${satirlar.length} satır]`;
  return cikti + dipnot;
}

function aramaDosyalari() {
  const sonuc = Object.keys(NOTLAR);
  const gez = (sanal, derinlik) => {
    let gercek;
    try { gercek = yolCoz(sanal); } catch { return; }
    if (!fs.statSync(gercek).isDirectory()) {
      if (ARAMA_UZANTI.has(path.extname(gercek).toLowerCase())) sonuc.push(sanal);
      return;
    }
    if (derinlik > 3) return;
    for (const g of fs.readdirSync(gercek, { withFileTypes: true })) {
      if (!g.name.startsWith('.') && !YASAK_AD.test(g.name)) gez(`${sanal}/${g.name}`, derinlik + 1);
    }
  };
  ARAMA_KLASORLERI.forEach((k) => gez(k, 0));
  return sonuc;
}

function ara({ ifade, azami = 40 } = {}) {
  const aranan = String(ifade || '').toLocaleLowerCase('tr');
  if (!aranan) throw new Error('ifade boş olamaz.');
  const sinir = Math.min(200, Math.max(1, Math.floor(azami)));
  const bulunan = [];
  for (const sanal of aramaDosyalari()) {
    let icerik;
    try { icerik = metinOku(yolCoz(sanal)); } catch { continue; }
    const satirlar = icerik.split(/\r?\n/);
    for (let i = 0; i < satirlar.length && bulunan.length < sinir; i++) {
      if (satirlar[i].toLocaleLowerCase('tr').includes(aranan)) {
        bulunan.push(`${sanal}:${i + 1}: ${satirlar[i].trim().slice(0, 400)}`);
      }
    }
    if (bulunan.length >= sinir) break;
  }
  return bulunan.length ? bulunan.join('\n') : 'Eşleşme yok.';
}

const YOL_OZ = { yol: { type: 'string', description: 'Örn. notlar/guncel-durum.md, proje/scripts/kur.py, model/master_veriseti.csv' } };
const ARACLAR = [
  { name: 'dosya_listele', description: 'Çatı GES projesindeki klasörü listeler. Yol verilmezse kök görünümü (notlar, proje, model).',
    inputSchema: { type: 'object', properties: { yol: { type: 'string', description: 'Boş, "notlar", "proje", "proje/scripts", "model"...' } } }, fn: dosyaListele },
  { name: 'dosya_oku', description: 'Çatı GES projesinden bir metin dosyasını satır aralığıyla okur (salt okunur). Büyük dosyalarda dipnottaki baslangic değeriyle devam et.',
    inputSchema: { type: 'object', required: ['yol'], properties: { ...YOL_OZ, baslangic: { type: 'integer', description: '1 tabanlı ilk satır' }, satir_sayisi: { type: 'integer', description: 'En çok 1000, varsayılan 300' } } }, fn: dosyaOku },
  { name: 'ara', description: 'Proje notları, scriptler ve raporlarda büyük/küçük harf duyarsız düz metin arar; dosya:satır döndürür.',
    inputSchema: { type: 'object', required: ['ifade'], properties: { ifade: { type: 'string' }, azami: { type: 'integer', description: 'En çok 200, varsayılan 40' } } }, fn: ara },
];

const TALIMAT = 'Çatı GES (güneş paneli) bitirme projesinin salt okunur bilgileri. Proje sorularında önce notlar/guncel-durum.md dosyasının başını oku; ayrıntı için ara aracıyla notlar/calisma-gunlugu.md içinde arama yap. Kaydetme yeteneği yoktur.';

function isle(msg) {
  const { id, method, params } = msg;
  if (id === undefined || id === null) return null; // bildirim
  const yanit = (result) => ({ jsonrpc: '2.0', id, result });
  switch (method) {
    case 'initialize':
      return yanit({ protocolVersion: (params && params.protocolVersion) || '2025-06-18', capabilities: { tools: {} },
        serverInfo: { name: 'cati-gunes', version: '1.0.0' }, instructions: TALIMAT });
    case 'ping': return yanit({});
    case 'tools/list':
      return yanit({ tools: ARACLAR.map(({ name, description, inputSchema }) => ({ name, description, inputSchema,
        annotations: { readOnlyHint: true, openWorldHint: false } })) });
    case 'tools/call': {
      const arac = ARACLAR.find((a) => a.name === (params && params.name));
      if (!arac) return { jsonrpc: '2.0', id, error: { code: -32602, message: 'Bilinmeyen araç' } };
      try {
        return yanit({ content: [{ type: 'text', text: arac.fn((params && params.arguments) || {}) }] });
      } catch (e) {
        const mesaj = e.code === 'ENOENT' ? 'Dosya bulunamadı.' : e.message;
        return yanit({ isError: true, content: [{ type: 'text', text: mesaj }] });
      }
    }
    default:
      return { jsonrpc: '2.0', id, error: { code: -32601, message: 'Desteklenmeyen yöntem' } };
  }
}

readline.createInterface({ input: process.stdin }).on('line', (satir) => {
  if (!satir.trim()) return;
  let msg;
  try { msg = JSON.parse(satir); } catch { return; }
  const cevap = isle(msg);
  if (cevap) process.stdout.write(JSON.stringify(cevap) + '\n');
});
