// CatiGunes web sayfasi: veriyi /api uzerinden veritabanindan okur.

// ---- sabitler -------------------------------------------------------
// NPV skalasi (trafik isigi): kirmizi (en dusuk getiri) -> turuncu -> sari -> acik yesil -> koyu yesil (en yuksek).
// Tum catilarda NPV pozitif; kirmizi zarar degil, en dusuk getiri sinifi.
// Komsu siniflar renk korlugunde de ayrisiyor (validate_palette.js: CVD dE 15.0, normal dE 19.4).
const SINIFLAR = [
  { ust: 1e6, renk: "#c62828" },
  { ust: 5e6, renk: "#f57c00" },
  { ust: 10e6, renk: "#fdd835" },
  { ust: 25e6, renk: "#7cb342" },
  { ust: Infinity, renk: "#1b5e20" },
];
const SINIF_ETIKET = ["0", "1", "5", "10", "25", "+"];
const GES_RENK = "#94a3b8";
const SECIM_RENK = "#22d3ee";
const POLIGON_ESIGI = 15; // bu yakinliktan itibaren cati sekilleri, oncesinde noktalar
const DETAY_GENISLIK = 340; // detay kartinin haritada kapladigi genislik (kart + bosluk)

const TUR_AD = {
  sanayi: "Sanayi çatısı",
  sanayi_disi: "Sanayi dışı bina",
  okul: "Okul",
  hastane: "Hastane",
  universite: "Üniversite",
};
const BOLGE_AD = { ataturk_osb: "Atatürk OSB", cigli_kamu: "Çiğli" };
const KAYNAK_AD = {
  sam: "uydu görüntüsünden otomatik çıkarıldı (SAM)",
  insan: "elle çizildi",
  ayak_izi: "kayıtlı bina ayak izinden alındı",
};
const GRUP_AD = { sanayi: "Sanayide", kamu: "Kamuda" };
const GRUP_TURLER = { sanayi: ["sanayi"], kamu: ["okul", "hastane", "universite"] };
// sira saglamligi: hangi listede kalma orani gosteriliyor
const ORAN_ACIKLAMA = {
  "": "senaryolarda ilk 100'de kalma",
  sanayi: "senaryolarda sanayi ilk 50'sinde kalma",
  kamu: "senaryolarda kamu ilk 20'sinde kalma",
};
const ORAN_KISA = { "": "ilk 100'de", sanayi: "sanayi ilk 50'sinde", kamu: "kamu ilk 20'sinde" };
const GRUP_RENK = { sanayi: "#ea580c", kamu: "#0284c7", diger: "#94a3b8" };
const TARAMA_AD = { "2026-11_ara_rapor": "ara rapor verisi" };

// ---- sayi bicimleri -------------------------------------------------
const tr = (x, b = 0) =>
  Number(x).toLocaleString("tr-TR", { minimumFractionDigits: b, maximumFractionDigits: b });

function para(x) {
  if (x === null || x === undefined) return ["–", ""];
  const m = Math.abs(x);
  if (m >= 1e9) return [tr(x / 1e9, 2), "milyar TL"];
  if (m >= 1e6) return [tr(x / 1e6, 1), "milyon TL"];
  if (m >= 1e3) return [tr(x / 1e3, 0), "bin TL"];
  return [tr(x), "TL"];
}
const tl = (x) => para(x).join(" ");
// iki para degerini ayni birimle yazar: "12,3 – 69,0 milyon TL"
function aralikYazi(a, b) {
  const m = Math.max(Math.abs(a), Math.abs(b));
  const [bol, birim, d] = m >= 1e9 ? [1e9, "milyar TL", 2] : m >= 1e6 ? [1e6, "milyon TL", 1] : [1e3, "bin TL", 0];
  const f = (x) => { const y = Number((x / bol).toFixed(d)); return tr(y === 0 ? 0 : y, d); };
  return `${f(a)} – ${f(b)} ${birim}`;
}
const guc = (kwp) => (kwp >= 1000 ? tr(kwp / 1000, 2) + " MW" : tr(kwp, 0) + " kWp");
const enerji = (kwh) => (kwh >= 1e6 ? tr(kwh / 1e6, 2) + " GWh" : tr(kwh / 1e3, 0) + " MWh");
const kacis = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const telefon = () => window.innerWidth <= 760;

function renk(p) {
  if (p.panel_durumu === "tam_dolu") return GES_RENK;
  return SINIFLAR.find((s) => p.npv_tl < s.ust).renk;
}

async function getir(yol) {
  const r = await fetch(yol);
  if (!r.ok) throw new Error(yol + " → " + r.status);
  return r.json();
}

// ---- harita ---------------------------------------------------------
const haritaKap = document.getElementById("harita-kap");
const harita = L.map("harita", {
  zoomControl: false, zoomSnap: 0.5, scrollWheelZoom: false, maxBoundsViscosity: 1.0,
}).setView([38.49, 27.0], 13);
L.control.zoom({ position: "topright" }).addTo(harita);
harita.createPane("etiketler").style.zIndex = 350; // altligin ustu, catilarin alti

// sayfa kaydirilirken harita yakinlasmasin: tekerlek, haritaya tiklayinca acilir
const tekerlekIpucu = document.getElementById("tekerlek-ipucu");
let ipucuZamani = null;
harita.on("click focus", () => harita.scrollWheelZoom.enable());
haritaKap.addEventListener("mouseleave", () => harita.scrollWheelZoom.disable());
haritaKap.addEventListener("wheel", () => {
  if (harita.scrollWheelZoom.enabled()) return;
  tekerlekIpucu.hidden = false;
  clearTimeout(ipucuZamani);
  ipucuZamani = setTimeout(() => { tekerlekIpucu.hidden = true; }, 1100);
}, { passive: true });

const ALTLIKLAR = {
  uydu: [
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 20, maxNativeZoom: 19, attribution: "Görüntü © Esri, Maxar, Earthstar Geographics",
    }),
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 20, maxNativeZoom: 19, pane: "etiketler", opacity: 0.85,
    }),
  ],
  // Esri gri altliklar 16. seviyeye kadar veri verir, otesinde buyutulerek gosterilir
  acik: [
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 20, maxNativeZoom: 16, attribution: "Harita © Esri, HERE, Garmin, © OpenStreetMap katkıcıları",
    }),
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 20, maxNativeZoom: 16, pane: "etiketler",
    }),
  ],
  koyu: [
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 20, maxNativeZoom: 16, attribution: "Harita © Esri, HERE, Garmin, © OpenStreetMap katkıcıları",
    }),
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 20, maxNativeZoom: 16, pane: "etiketler",
    }),
  ],
};
let altlik = null;
function altlikSec(ad) {
  if (altlik) ALTLIKLAR[altlik].forEach((k) => harita.removeLayer(k));
  ALTLIKLAR[ad].forEach((k) => k.addTo(harita));
  altlik = ad;
  harita.getContainer().classList.toggle("uydu-koyu", ad === "uydu");
  document.querySelectorAll("#altlik button").forEach((b) => b.classList.toggle("secili", b.dataset.altlik === ad));
  if (bolgeKatmani) bolgeKatmani.setStyle(bolgeStili());
}
document.querySelectorAll("#altlik button").forEach((b) => b.addEventListener("click", () => altlikSec(b.dataset.altlik)));

// ---- durum ----------------------------------------------------------
const durum = { grup: "", gesGoster: true };
let tumVeri = null;
let ozetVeri = null;
let seciliId = null;
let vurgu = null; // vurgulanan cati_id'ler (Set) ya da null
let poligonKatmani = null;
let noktaKatmani = null;
let bolgeKatmani = null;
let catiSiniri = null; // tum catilarin kapsadigi alan
const katmanlar = new Map(); // cati_id -> { poligon, nokta, p }

// ---- cati stilleri --------------------------------------------------
function poligonStili(p) {
  const id = p.cati_id, secili = id === seciliId;
  const dolu = p.panel_durumu === "tam_dolu";
  const icinde = !vurgu || vurgu.has(id) || secili; // secili cati vurgu disinda olsa da soluklasmaz
  return {
    color: secili ? SECIM_RENK : vurgu && icinde ? SECIM_RENK : "#ffffff",
    weight: secili ? 3 : vurgu && icinde ? 2 : 0.7,
    opacity: icinde || secili ? 0.95 : 0.3,
    fillColor: renk(p),
    fillOpacity: !icinde ? 0.1 : dolu ? 0.4 : 0.78,
  };
}

const yaricap = (p) => (p.panel_durumu === "tam_dolu" ? 3 : 3 + Math.sqrt(p.kwp) / 5.5);

function noktaStili(p) {
  const id = p.cati_id, secili = id === seciliId;
  const icinde = !vurgu || vurgu.has(id) || secili;
  return {
    radius: yaricap(p),
    color: secili || (vurgu && icinde) ? SECIM_RENK : "#ffffff",
    weight: secili ? 2.5 : vurgu && icinde ? 1.8 : 0.8,
    opacity: icinde ? 0.95 : 0.25,
    fillColor: renk(p),
    fillOpacity: !icinde ? 0.12 : p.panel_durumu === "tam_dolu" ? 0.55 : 0.9,
  };
}

function stilleriYenile() {
  katmanlar.forEach(({ poligon, nokta, p }) => {
    poligon.setStyle(poligonStili(p));
    nokta.setStyle(noktaStili(p));
    const secili = p.cati_id === seciliId;
    [poligon, nokta].forEach((k) => k.getElement()?.classList.toggle("secili-cati", secili));
    if (secili || (vurgu && vurgu.has(p.cati_id))) { poligon.bringToFront(); nokta.bringToFront(); }
  });
}

function gorunur(p) {
  if (durum.grup && p.grup !== durum.grup) return false;
  if (!durum.gesGoster && p.panel_durumu === "tam_dolu") return false;
  return true;
}

function ipucu(p) {
  const ad = p.kurum_ad || `${TUR_AD[p.tur]} ${p.cati_id}`;
  const deger = p.panel_durumu === "tam_dolu" ? "Mevcut GES" : tl(p.npv_tl);
  return `${kacis(ad)} · <b>${deger}</b>`;
}

function catilariCiz() {
  if (poligonKatmani) harita.removeLayer(poligonKatmani);
  if (noktaKatmani) harita.removeLayer(noktaKatmani);
  katmanlar.clear();
  poligonKatmani = L.featureGroup();
  noktaKatmani = L.featureGroup();
  const ipucuAyar = { sticky: true, className: "ipucu", direction: "top", offset: [0, -10] };

  L.geoJSON(tumVeri, { filter: (f) => gorunur(f.properties) }).eachLayer((g) => {
    const p = g.feature.properties;
    g.setStyle(poligonStili(p));
    const nokta = L.circleMarker(g.getBounds().getCenter(), noktaStili(p));
    for (const k of [g, nokta]) {
      k.bindTooltip(ipucu(p), ipucuAyar);
      k.on("click", () => catiSec(p.cati_id, false));
      k.on("mouseover", () => k.setStyle({ weight: 3, color: SECIM_RENK }));
      k.on("mouseout", () => k.setStyle(k === g ? poligonStili(p) : noktaStili(p)));
    }
    poligonKatmani.addLayer(g);
    noktaKatmani.addLayer(nokta);
    katmanlar.set(p.cati_id, { poligon: g, nokta, p });
  });
  katmanGorunumu();
}

function katmanGorunumu() {
  if (!poligonKatmani) return;
  const yakin = harita.getZoom() >= POLIGON_ESIGI;
  const [goster, gizle] = yakin ? [poligonKatmani, noktaKatmani] : [noktaKatmani, poligonKatmani];
  if (harita.hasLayer(gizle)) harita.removeLayer(gizle);
  if (!harita.hasLayer(goster)) goster.addTo(harita);
  stilleriYenile();
}
harita.on("zoomend", katmanGorunumu);

// detay kartinin kapladigi alani hesaba katarak bir alana sigdir
function sigdir(sinir, ucus, maxZoom = 18) {
  const detayAcik = haritaKap.classList.contains("detay-acik");
  const ayar = telefon()
    ? { maxZoom, paddingTopLeft: [20, 60], paddingBottomRight: [20, detayAcik ? haritaKap.clientHeight * 0.6 + 20 : 60] }
    : { maxZoom, paddingTopLeft: [30, 60], paddingBottomRight: [detayAcik ? DETAY_GENISLIK + 30 : 30, 60] };
  if (ucus) harita.flyToBounds(sinir, { ...ayar, duration: 0.9 });
  else harita.fitBounds(sinir, ayar);
}

// harita calisma alaninin cok disina cikmasin: en uzak gorunum tum catilarin sigdigi seviye
function haritayiSinirla() {
  catiSiniri = poligonKatmani.getBounds();
  harita.setMaxBounds(catiSiniri.pad(0.12));
  harita.setMinZoom(Math.floor(harita.getBoundsZoom(catiSiniri) * 2) / 2);
}

// acilis gorunumu: uctaki birkac daginik bina yerine catilarin yogunlastigi cekirdek alan
function cekirdekSinir() {
  const merkezler = [...katmanlar.values()].map((k) => k.poligon.getBounds().getCenter());
  const yuzdelik = (dizi, q) => { const s = [...dizi].sort((a, b) => a - b); return s[Math.floor(q * (s.length - 1))]; };
  const enlem = merkezler.map((m) => m.lat), boylam = merkezler.map((m) => m.lng);
  return L.latLngBounds([yuzdelik(enlem, 0.03), yuzdelik(boylam, 0.03)], [yuzdelik(enlem, 0.97), yuzdelik(boylam, 0.97)]);
}

// ---- bolge sinirlari ------------------------------------------------
function bolgeStili() {
  const koyuZemin = altlik !== "acik";
  return { color: koyuZemin ? "#ffffff" : "#334155", weight: 1.5, opacity: 0.7, dashArray: "6 6", fill: false };
}

function bolgeleriCiz(veri) {
  bolgeKatmani = L.geoJSON(veri, { style: bolgeStili(), interactive: false }).addTo(harita);
  // yalniz OSB etiketlenir; Cigli adi altligin kendi yer adlarinda zaten var
  bolgeKatmani.eachLayer((k) => {
    if (k.feature.properties.bolge_kod !== "ataturk_osb") return;
    L.tooltip({ permanent: true, direction: "center", className: "bolge-etiket", interactive: false })
      .setLatLng(k.getCenter()).setContent("Atatürk OSB").addTo(harita);
  });
}

// ---- detay karti ----------------------------------------------------
const detay = document.getElementById("detay");
const detayIcerik = document.getElementById("detay-icerik");

async function catiSec(id, yaklas) {
  if (!katmanlar.has(id) && tumVeri) filtreUygula("", true); // cati filtre yuzunden gizliyse goster
  seciliId = id;
  detay.hidden = false;
  haritaKap.classList.add("detay-acik");
  detay.scrollTop = 0;
  stilleriYenile();
  const k = katmanlar.get(id);
  if (yaklas && k) sigdir(k.poligon.getBounds(), true);
  else if (k && harita.getZoom() < POLIGON_ESIGI) sigdir(k.poligon.getBounds(), true, 17);
  document.querySelectorAll("#liste li").forEach((li) => li.classList.toggle("secili", Number(li.dataset.id) === id));
  detayIcerik.innerHTML = `<div class="d-ust"><p class="d-alt">Yükleniyor…</p></div>`;
  try {
    const c = await getir("/api/catilar/" + id);
    if (seciliId === id) {
      detay.style.setProperty("--d-renk", renk(c));
      detayIcerik.innerHTML = kartHtml(c);
    }
  } catch (e) {
    detayIcerik.innerHTML = `<div class="d-ust"><p class="d-alt">Bilgi alınamadı: ${kacis(e.message)}</p></div>`;
  }
}

function detayKapat() {
  detay.hidden = true;
  haritaKap.classList.remove("detay-acik");
  seciliId = null;
  stilleriYenile();
  document.querySelectorAll("#liste li").forEach((li) => li.classList.remove("secili"));
}
document.getElementById("detay-kapat").addEventListener("click", detayKapat);
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  detayKapat();
  if (typeof aDetayKapat === "function") aDetayKapat();
});

// sayfayi haritaya kaydirip sonra bir islem yapar
function haritayaGit(sonra) {
  const bolum = document.getElementById("harita-bolum");
  const ust = bolum.getBoundingClientRect().top;
  const gorunuyor = ust > -80 && ust < 120;
  if (!gorunuyor) bolum.scrollIntoView({ behavior: "smooth" });
  setTimeout(sonra, gorunuyor ? 0 : 600);
}

function kartHtml(c) {
  const baslik = c.kurum_ad || `Çatı ${c.cati_id}`;
  const alt = BOLGE_AD[c.bolge_kod] + (c.kurum_ad ? ` · çatı ${c.cati_id}` : "");
  const tamDolu = c.panel_durumu === "tam_dolu";

  let cipler = `<span class="cip">${TUR_AD[c.tur]}</span>`;
  if (tamDolu) cipler += `<span class="cip ges">Mevcut GES</span>`;
  else if (c.sira_grup) cipler += `<span class="cip sira">${GRUP_AD[c.grup]} ${c.sira_grup}. / ${c.grup_cati_sayisi}</span>`;
  else cipler += `<span class="cip sira">Genel ${c.sira_npv}. sırada</span>`;

  let h = `<div class="d-ust"><div class="d-cipler">${cipler}</div>
    <h3 class="d-baslik">${kacis(baslik)}</h3><div class="d-alt">${alt}</div></div>`;

  if (tamDolu) {
    h += `<dl class="d-izgara">
        <div><dt>Çatı alanı</dt><dd>${tr(c.cati_alan_m2)} m²</dd></div>
        <div><dt>Ek potansiyel</dt><dd>Yok<small>Çatı panelle dolu</small></dd></div>
      </dl>`;
    return h + notlar(c);
  }

  const [npvSayi, npvBirim] = para(c.npv_tl);
  h += `<div class="d-ana">
      <div class="d-ana-etiket">Net bugünkü değer</div>
      <div class="d-ana-deger">${npvSayi}<small>${npvBirim}</small></div>
      ${aralikHtml(c)}
    </div>
    <dl class="d-izgara">
      <div><dt>Yatırım</dt><dd>${tl(c.yatirim_tl)}</dd></div>
      <div><dt>Geri ödeme</dt><dd>${c.geri_odeme_yil} yıl</dd></div>
      <div><dt>Kurulabilir güç</dt><dd>${guc(c.kwp)}</dd></div>
      <div><dt>Yıllık üretim</dt><dd>${enerji(c.kwh_yil)}<small>${enerji(c.kwh_alt)} – ${enerji(c.kwh_ust)}</small></dd></div>
      <div><dt>Kullanılabilir alan</dt><dd>${tr(c.uygun_alan_m2)} m²${
        c.panel_durumu === "kismi_panel_dusuldu" ? "<small>Mevcut paneller düşüldü</small>" : ""}</dd></div>
      <div><dt>Kârlı senaryo</dt><dd>100'de ${Math.round(c.p_npv_poz * 100)}<small>10.000 senaryodan</small></dd></div>
    </dl>`;

  if (c.aciklama) {
    const bas = [["ozet", "Özet"], ["sira_nedeni", "Sıradaki yeri"], ["belirsizlik", "10.000 senaryo testi"], ["veri_guvenilirligi", "Veri"]];
    h += `<div class="d-aciklama">
      <div class="d-aciklama-bas"><span>Yorum</span><small>yapay zekâ ile veritabanından üretildi</small></div>
      ${bas.map(([k, ad]) => `<div class="d-yorum"><b>${ad}</b><p>${kacis(c.aciklama[k])}</p></div>`).join("")}
      <p class="d-varsayim">Hesap, üretilen elektriğin tamamının binada kullanıldığını varsayar; NPV bu yüzden bir üst değer olarak okunmalıdır.</p>
    </div>`;
    return h; // veri ve fiyat bilgisi yorumda yer aliyor
  }
  return h + notlar(c);
}

// olasi aralik cubugu: p10-p90 bandi, temel NPV isareti
function aralikHtml(c) {
  const alt = Math.min(0, c.npv_p10), ust = Math.max(c.npv_p90, c.npv_tl) * 1.05;
  const yuzde = (x) => ((x - alt) / (ust - alt)) * 100;
  const m = Math.max(Math.abs(c.npv_p10), Math.abs(c.npv_p90));
  const [b, birim, d] = m >= 1e6 ? [1e6, "milyon TL", 1] : [1e3, "bin TL", 0];
  const fmt = (x) => { const y = Number((x / b).toFixed(d)); return tr(y === 0 ? 0 : y, d); };
  return `<div class="aralik" title="10.000 senaryonun %80'i bu aralıkta">
      <div class="aralik-yol">
        <div class="aralik-bant" style="left:${yuzde(c.npv_p10)}%;width:${yuzde(c.npv_p90) - yuzde(c.npv_p10)}%;background:${renk(c)}"></div>
        <div class="aralik-isaret" style="left:${yuzde(c.npv_tl)}%"></div>
      </div>
      <div class="aralik-yazi">Olası aralık <b>${fmt(c.npv_p10)} – ${fmt(c.npv_p90)}</b> ${birim}</div>
      <div class="aralik-lejant">
        <span><i class="al-cizgi"></i>hesaplanan değer</span>
        <span><i class="al-bant" style="background:${renk(c)}"></i>10.000 senaryonun %80'i</span>
      </div>
    </div>`;
}

function notlar(c) {
  let n = `<div class="d-not">Çatı sınırı ${KAYNAK_AD[c.geometri_kaynagi]}.`;
  if (c.panel_durumu !== "tam_dolu") n += ` Elektrik fiyatı ${tr(c.tarife_kr_kwh, 1)} kr/kWh.`;
  if (c.supheli) n += `<span class="uyari">Otomatik çıkarım (SAM) şüpheli bulunduğu için kullanılmadı.</span>`;
  return n + "</div>";
}

// ---- gostergeler ----------------------------------------------------
function ozetToplam(grup) {
  const turler = grup ? GRUP_TURLER[grup] || [] : null;
  const satirlar = ozetVeri.satirlar.filter((s) => !turler || turler.includes(s.tur));
  const top = (a) => satirlar.reduce((t, s) => t + Number(s[a] || 0), 0);
  return { cati: top("cati"), mwp: top("mwp"), gwh: top("gwh_yil"), npv: top("npv_milyon_tl") * 1e6 };
}

function girisGostergeleri() {
  const t = ozetToplam("");
  const [npvS, npvB] = para(t.npv);
  document.getElementById("h-cati").textContent = tr(t.cati);
  document.getElementById("h-mwp").innerHTML = `${tr(t.mwp, 1)}<small>MWp</small>`;
  document.getElementById("h-gwh").innerHTML = `${tr(t.gwh, 1)}<small>GWh/yıl</small>`;
  document.getElementById("h-npv").innerHTML = `${npvS}<small>${npvB}</small>`;
}

function aracOzeti() {
  const t = ozetToplam(durum.grup);
  document.getElementById("arac-ozet").innerHTML =
    `<span><b>${tr(t.cati)}</b>çatı</span><span><b>${tr(t.mwp, 1)}</b>MWp</span><span><b>${para(t.npv)[0]}</b>${para(t.npv)[1]}</span>`;
}

function lejantCiz() {
  document.getElementById("lejant-serit").innerHTML = SINIFLAR.map((s) => `<i style="background:${s.renk}"></i>`).join("");
  document.getElementById("lejant-etiket").innerHTML = SINIF_ETIKET.map((e) => `<span>${e}</span>`).join("");
}

// ---- oncelik listesi ------------------------------------------------
async function listeCiz() {
  const g = durum.grup;
  const baslik = { "": "Öncelik sıralaması", sanayi: "Sanayi öncelik sırası", kamu: "Kamu öncelik sırası" };
  document.getElementById("liste-baslik").textContent = baslik[g] || baslik[""];
  document.getElementById("liste-rozet-aciklama").textContent = ORAN_ACIKLAMA[g] || ORAN_ACIKLAMA[""];
  const yol = "/api/siralama?olcut=npv&limit=25" + (g === "sanayi" || g === "kamu" ? "&grup=" + g : "");
  const liste = await getir(yol);
  // butun satirlar ayni olcekte: aralik cubuklari birbiriyle karsilastirilabilir
  const olcekAlt = Math.min(0, ...liste.map((c) => c.npv_p10));
  const olcekUst = Math.max(1, ...liste.map((c) => Math.max(c.npv_p90, c.npv_tl)));
  const konum = (x) => ((x - olcekAlt) / (olcekUst - olcekAlt)) * 100;
  const ol = document.getElementById("liste");
  ol.innerHTML = liste.map((c) => {
    const oran = g ? c.grup_ilk_orani : c.ilk100_orani;
    const sinif = oran >= 0.9 ? "guclu" : oran >= 0.5 ? "orta" : "";
    return `
    <li data-id="${c.cati_id}" class="${c.cati_id === seciliId ? "secili" : ""}">
      <span class="sira-no">${c.sira}</span>
      <span class="liste-orta">
        <span class="liste-ad">${kacis(c.kurum_ad || `${TUR_AD[c.tur]} ${c.cati_id}`)}</span>
        <span class="liste-alt">${c.kurum_ad ? TUR_AD[c.tur] + " · " : ""}${guc(c.kwp)} · ${c.geri_odeme_yil} yılda geri öder</span>
        <span class="liste-aralik" title="Olası NPV aralığı: ${aralikYazi(c.npv_p10, c.npv_p90)}">
          <i class="bant" style="left:${konum(c.npv_p10)}%;width:${konum(c.npv_p90) - konum(c.npv_p10)}%"></i>
          <i class="temel" style="left:${konum(c.npv_tl)}%"></i>
        </span>
      </span>
      <span class="liste-deger">
        <span>${tr(c.npv_tl / 1e6, 1)}<small>milyon TL</small></span>
        <span class="rozet ${sinif}" title="${ORAN_KISA[g] || ORAN_KISA[""]} kalma oranı: %${Math.round(oran * 100)} (10.000 senaryo)">%${Math.round(oran * 100)}</span>
      </span>
    </li>`;
  }).join("");
  ol.querySelectorAll("li").forEach((li) => li.addEventListener("click", () => catiSec(Number(li.dataset.id), true)));
}

function filtreUygula(grup, gesGoster = durum.gesGoster) {
  durum.grup = grup;
  durum.gesGoster = gesGoster;
  document.querySelectorAll("#grup-secim button").forEach((x) => x.classList.toggle("secili", x.dataset.grup === grup));
  document.getElementById("ges-goster").checked = gesGoster;
  catilariCiz();
  aracOzeti();
  listeCiz();
}

document.querySelectorAll("#grup-secim button").forEach((b) =>
  b.addEventListener("click", () => {
    detayKapat();
    vurgu = null;
    document.getElementById("vurgu-cip").hidden = true;
    filtreUygula(b.dataset.grup);
    if (poligonKatmani.getLayers().length) sigdir(poligonKatmani.getBounds(), true, 16);
  })
);
document.getElementById("ges-goster").addEventListener("change", (e) => filtreUygula(durum.grup, e.target.checked));

// ---- vurgu ----------------------------------------------------------
// haritada bir grup catiyi vurgular; etiket ustteki bilgi cipinde gosterilir
function vurguAyarla(idler, etiket = "") {
  vurgu = idler && idler.length ? new Set(idler) : null;
  if (vurgu && (durum.grup || !durum.gesGoster)) filtreUygula("", true); // vurgulananlarin hepsi gorunsun
  stilleriYenile();
  const cip = document.getElementById("vurgu-cip");
  cip.hidden = !vurgu;
  if (vurgu) document.getElementById("vurgu-yazi").innerHTML = etiket || `<b>${tr(vurgu.size)}</b> çatı vurgulandı`;
  if (!vurgu) return;
  const sinir = L.latLngBounds([]);
  vurgu.forEach((id) => { const k = katmanlar.get(id); if (k) sinir.extend(k.poligon.getBounds()); });
  if (sinir.isValid()) setTimeout(() => sigdir(sinir, true, 17), 80);
}
document.getElementById("vurgu-kaldir").addEventListener("click", () => vurguAyarla(null));

// ---- analiz ---------------------------------------------------------
const aIpucu = document.getElementById("a-ipucu");
const SVG = "http://www.w3.org/2000/svg";
let analizVeri = null;
let analizGrup = "";
let butceOlcut = "npv";

const adi = (c) => c.kurum_ad || `${TUR_AD[c.tur]} ${c.cati_id}`;
const ort = (dizi, f) => dizi.reduce((t, x) => t + f(x), 0) / Math.max(dizi.length, 1);
const toplam = (dizi, f) => dizi.reduce((t, x) => t + f(x), 0);
const analizSatirlari = () => analizVeri.filter((c) => !analizGrup || c.grup === analizGrup);
const oranAl = (c) => (analizGrup ? c.grup_ilk_orani : c.ilk100_orani);

function ipucuGoster(e, html) {
  aIpucu.innerHTML = html;
  aIpucu.hidden = false;
  const g = aIpucu.offsetWidth, y = aIpucu.offsetHeight;
  const x = e.clientX + 14 + g > window.innerWidth ? e.clientX - g - 14 : e.clientX + 14;
  const yy = e.clientY + 14 + y > window.innerHeight ? e.clientY - y - 14 : e.clientY + 14;
  aIpucu.style.left = x + "px";
  aIpucu.style.top = yy + "px";
}
const ipucuGizle = () => { aIpucu.hidden = true; };
window.addEventListener("scroll", ipucuGizle, { passive: true });

// SVG oge olusturma yardimcisi
function el(ad, nitelik = {}, metin) {
  const e = document.createElementNS(SVG, ad);
  for (const [k, v] of Object.entries(nitelik)) e.setAttribute(k, v);
  if (metin !== undefined) e.textContent = metin;
  return e;
}

// eksen icin yuvarlak adim
function adimSec(enBuyuk, hedef = 5) {
  const ham = enBuyuk / hedef;
  const us = Math.pow(10, Math.floor(Math.log10(ham)));
  return [1, 2, 2.5, 5, 10].map((k) => k * us).find((a) => a >= ham);
}

document.querySelectorAll("#analiz-grup button").forEach((b) =>
  b.addEventListener("click", () => { analizGrup = b.dataset.grup; analiziCiz(); })
);

function analiziCiz() {
  document.querySelectorAll("#analiz-grup button").forEach((b) => b.classList.toggle("secili", b.dataset.grup === analizGrup));
  bulgulariCiz();
  butceAyarla();
  paretoCiz();
  karsilastirmaCiz();
  saglamlikCiz();
}

// -- bulgu kartlari: hepsi veriden hesaplanir
function bulgulariCiz() {
  const s = analizSatirlari();
  const npvToplam = toplam(s, (c) => c.npv_tl);
  const sirali = [...s].sort((a, b) => b.npv_tl - a.npv_tl);
  let birikim = 0, yari = 0;
  for (const c of sirali) { birikim += c.npv_tl; yari++; if (birikim >= npvToplam / 2) break; }
  const karli = s.filter((c) => c.p_npv_poz >= 0.9).length;
  const saglam = s.filter((c) => oranAl(c) >= 0.9).length;
  const liste = ORAN_KISA[analizGrup] || ORAN_KISA[""];
  document.getElementById("a-bulgular").innerHTML = `
    <div class="bulgu">
      <div class="bulgu-etiket">Yoğunlaşma</div>
      <div class="bulgu-deger">${tr(yari)}<small>çatı</small></div>
      <div class="bulgu-metin">Toplam NPV'nin yarısını tek başına oluşturuyor. Bu, ${tr(s.length)} çatının yalnızca %${tr((yari / s.length) * 100, 0)} kadarı.</div>
    </div>
    <div class="bulgu">
      <div class="bulgu-etiket">10.000 senaryo testi</div>
      <div class="bulgu-deger">${tr(karli)}<small>/ ${tr(s.length)} çatı</small></div>
      <div class="bulgu-metin">Maliyet, kur, fiyat ve faiz değiştirilen senaryoların en az %90'ında kârlı kalıyor.</div>
    </div>
    <div class="bulgu">
      <div class="bulgu-etiket">Her koşulda öncelikli</div>
      <div class="bulgu-deger">${tr(saglam)}<small>çatı</small></div>
      <div class="bulgu-metin">Senaryoların en az %90'ında ${liste} kalıyor. Varsayımlar değişse de öncelikleri bozulmuyor.</div>
    </div>`;
}

// -- butce senaryosu
const butceGirdi = document.getElementById("butce");
function butceAyarla() {
  const s = analizSatirlari();
  const enFazla = Math.ceil(toplam(s, (c) => c.yatirim_tl) / 25e6) * 25;
  butceGirdi.max = enFazla;
  if (Number(butceGirdi.value) > enFazla) butceGirdi.value = Math.min(500, enFazla);
  document.getElementById("butce-max").textContent = tl(enFazla * 1e6);
  butceHesapla();
}

function butceSecimi() {
  const butce = Number(butceGirdi.value) * 1e6;
  const sirali = [...analizSatirlari()].sort(butceOlcut === "npv"
    ? (a, b) => b.npv_tl - a.npv_tl
    : (a, b) => b.npv_tl / b.yatirim_tl - a.npv_tl / a.yatirim_tl);
  const secilen = [];
  let harcanan = 0;
  for (const c of sirali) { // sirayla ekle, sigmayani atla
    if (harcanan + c.yatirim_tl <= butce) { secilen.push(c); harcanan += c.yatirim_tl; }
  }
  return { butce, secilen, harcanan };
}

function butceHesapla() {
  const { secilen, harcanan } = butceSecimi();
  document.getElementById("butce-yazi").textContent = tr(Number(butceGirdi.value));
  const [npvS, npvB] = para(toplam(secilen, (c) => c.npv_tl));
  document.getElementById("butce-sonuc").innerHTML = `
    <div><dt>Çatı</dt><dd>${tr(secilen.length)}</dd></div>
    <div><dt>Kurulu güç</dt><dd>${tr(toplam(secilen, (c) => c.kwp) / 1000, 1)}<small>MW</small></dd></div>
    <div><dt>Yıllık üretim</dt><dd>${tr(toplam(secilen, (c) => c.kwh_yil) / 1e6, 1)}<small>GWh</small></dd></div>
    <div><dt>Toplam NPV</dt><dd>${npvS}<small>${npvB.replace(" TL", "")}</small></dd></div>`;
  // harcanan butcenin gruplara dagilimi (ince parcali cubuk)
  const gruplar = ["sanayi", "kamu", "diger"].map((g) => ({
    g, t: toplam(secilen.filter((c) => c.grup === g), (c) => c.yatirim_tl), n: secilen.filter((c) => c.grup === g).length,
  })).filter((x) => x.n);
  const ad = { sanayi: "Sanayi", kamu: "Kamu", diger: "Diğer" };
  document.getElementById("butce-grup").innerHTML = secilen.length ? `
    <div class="butce-grup-bar">${gruplar.map((x) => `<i style="flex:${x.t};background:${GRUP_RENK[x.g]}"></i>`).join("")}</div>
    <div class="butce-grup-yazi">${gruplar.map((x) => `<span><i style="background:${GRUP_RENK[x.g]}"></i>${ad[x.g]} ${tr(x.n)} çatı · ${tl(x.t)}</span>`).join("")}
      <span style="margin-left:auto">harcanan ${tl(harcanan)}</span></div>` : `<div class="butce-grup-yazi">Bu bütçe en küçük yatırıma bile yetmiyor.</div>`;
}
butceGirdi.addEventListener("input", butceHesapla);
document.querySelectorAll("#butce-olcut button").forEach((b) =>
  b.addEventListener("click", () => {
    butceOlcut = b.dataset.olcut;
    document.querySelectorAll("#butce-olcut button").forEach((x) => x.classList.toggle("secili", x === b));
    butceHesapla();
  })
);
document.getElementById("butce-goster").addEventListener("click", () => {
  const { secilen } = butceSecimi();
  detayKapat();
  haritayaGit(() => vurguAyarla(secilen.map((c) => c.cati_id),
    `Bütçe senaryosu · <b>${tr(Number(butceGirdi.value))} milyon TL</b> · ${tr(secilen.length)} çatı`));
});

// -- yogunlasma egrisi (birikimli NPV payi)
function paretoCiz() {
  const kap = document.getElementById("pareto");
  const s = [...analizSatirlari()].sort((a, b) => b.npv_tl - a.npv_tl);
  const n = s.length, npvToplam = toplam(s, (c) => c.npv_tl);
  let birikim = 0;
  const pay = [0, ...s.map((c) => (birikim += c.npv_tl) / npvToplam * 100)];

  const G = 520, Y = 250, sol = 40, sag = 14, ust = 12, alt = 34;
  const x = (i) => sol + (i / n) * (G - sol - sag);
  const y = (p) => ust + (1 - p / 100) * (Y - ust - alt);
  const svg = el("svg", { viewBox: `0 0 ${G} ${Y}`, role: "img", "aria-label": "Birikimli NPV payı eğrisi" });

  const izgara = el("g", { class: "g-izgara" }), eksen = el("g", { class: "g-eksen" });
  for (const p of [0, 25, 50, 75, 100]) {
    izgara.append(el("line", { x1: sol, x2: G - sag, y1: y(p), y2: y(p) }));
    eksen.append(el("text", { x: sol - 8, y: y(p) + 3.5, "text-anchor": "end" }, `%${p}`));
  }
  const adim = adimSec(n, 4);
  for (let i = 0; i <= n; i += adim) eksen.append(el("text", { x: x(i), y: Y - alt + 16, "text-anchor": "middle" }, tr(i)));
  eksen.append(el("text", { x: (sol + G - sag) / 2, y: Y - 4, "text-anchor": "middle" }, "Çatı sayısı (NPV'ye göre sıralı)"));
  svg.append(izgara, eksen);

  const nokta = pay.map((p, i) => `${x(i).toFixed(1)},${y(p).toFixed(1)}`);
  svg.append(el("path", { d: `M${x(0)},${y(0)} L${nokta.join(" L")} L${x(n)},${y(0)} Z`, fill: "#ea580c", "fill-opacity": 0.1 }));
  svg.append(el("path", { d: `M${nokta.join(" L")}`, fill: "none", stroke: "#ea580c", "stroke-width": 2, "stroke-linejoin": "round" }));

  // %50 ve %80 esikleri: secici etiket
  for (const esik of [50, 80]) {
    const i = pay.findIndex((p) => p >= esik);
    svg.append(el("line", { x1: x(i), x2: x(i), y1: y(esik), y2: y(0), stroke: "#cbd5e1", "stroke-width": 1 }));
    svg.append(el("circle", { cx: x(i), cy: y(esik), r: 4.5, fill: "#ea580c", stroke: "#fff", "stroke-width": 2 }));
    const sagda = x(i) < G * 0.62;
    svg.append(el("text", { x: x(i) + (sagda ? 9 : -9), y: y(esik) + 4, "text-anchor": sagda ? "start" : "end", class: "g-etiket-metin" },
      `İlk ${tr(i)} çatı → %${esik}`));
  }

  // fareyle gezinme: dikey cizgi + nokta + ipucu
  const cizgi = el("line", { y1: ust, y2: y(0), stroke: "#0f172a", "stroke-width": 1, opacity: 0 });
  const imlec = el("circle", { r: 4.5, fill: "#ea580c", stroke: "#fff", "stroke-width": 2, opacity: 0 });
  const alan = el("rect", { x: sol, y: ust, width: G - sol - sag, height: Y - ust - alt, fill: "transparent" });
  svg.append(cizgi, imlec, alan);
  alan.addEventListener("mousemove", (e) => {
    const r = svg.getBoundingClientRect();
    const vx = ((e.clientX - r.left) / r.width) * G;
    const i = Math.max(1, Math.min(n, Math.round(((vx - sol) / (G - sol - sag)) * n)));
    cizgi.setAttribute("x1", x(i)); cizgi.setAttribute("x2", x(i)); cizgi.setAttribute("opacity", 0.25);
    imlec.setAttribute("cx", x(i)); imlec.setAttribute("cy", y(pay[i])); imlec.setAttribute("opacity", 1);
    ipucuGoster(e, `İlk <b>${tr(i)}</b> çatı<br>Toplam NPV payı <b>%${tr(pay[i], 1)}</b><br>${tl((pay[i] / 100) * npvToplam)}`);
  });
  alan.addEventListener("mouseleave", () => { cizgi.setAttribute("opacity", 0); imlec.setAttribute("opacity", 0); ipucuGizle(); });
  kap.replaceChildren(svg);
}

// -- sanayi ve kamu karsilastirmasi (kucuk coklu grafikler, her olcu kendi ekseninde)
function karsilastirmaCiz() {
  const gr = { sanayi: analizVeri.filter((c) => c.grup === "sanayi"), kamu: analizVeri.filter((c) => c.grup === "kamu") };
  const olculer = [
    { ad: "Kurulan kWp başına NPV", not: "yüksek daha iyi", f: (s) => ort(s, (c) => c.npv_tl / c.kwp), yaz: (v) => tr(v) + " TL" },
    { ad: "Ortalama geri ödeme", not: "düşük daha iyi", f: (s) => ort(s, (c) => c.geri_odeme_yil), yaz: (v) => tr(v, 1) + " yıl" },
    { ad: "Kârlı çıkan senaryo payı", not: "10.000 senaryo ortalaması", f: (s) => ort(s, (c) => c.p_npv_poz) * 100, yaz: (v) => "%" + tr(v, 1) },
  ];
  const ad = { sanayi: "Sanayi", kamu: "Kamu" };
  let html = olculer.map((o) => {
    const d = { sanayi: o.f(gr.sanayi), kamu: o.f(gr.kamu) };
    const enB = Math.max(d.sanayi, d.kamu) * 1.25; // deger etiketine yer kalsin
    return `<div class="karsi-blok"><div class="karsi-baslik">${o.ad}<span>${o.not}</span></div>
      ${["sanayi", "kamu"].map((g) => `<div class="karsi-satir">${ad[g]}
        <div class="karsi-yol"><i style="width:${(d[g] / enB) * 100}%;background:${GRUP_RENK[g]}"></i>
        <b style="left:${(d[g] / enB) * 100}%">${o.yaz(d[g])}</b></div></div>`).join("")}</div>`;
  }).join("");
  const kat = olculer[0].f(gr.kamu) / olculer[0].f(gr.sanayi);
  html += `<div class="karsi-not">Kamu binaları kurulan her kWp başına sanayinin <b>${tr(kat, 1)} katı</b> getiri sağlıyor.
    Kamu elektrik tarifesi daha yüksek olduğu için aynı üretim daha fazla tasarruf ediyor.</div>`;
  document.getElementById("karsilastirma").innerHTML = html;
}

// -- siralama saglamligi: ilk 15 catinin olasi NPV araligi + ust sirada kalma orani
function saglamlikCiz() {
  const kap = document.getElementById("saglamlik");
  const siraAl = (c) => (analizGrup ? c.sira_grup : c.sira_npv);
  const s = analizSatirlari().filter((c) => siraAl(c)).sort((a, b) => siraAl(a) - siraAl(b)).slice(0, 15);
  document.getElementById("saglam-aciklama").textContent =
    `İlk 15 çatının olası NPV aralığı ve 10.000 senaryoda ${ORAN_KISA[analizGrup] || ORAN_KISA[""]} kalma oranı. Satıra tıklayınca çatı haritada açılır.`;

  const G = 520, satirY = 26, ust = 6, alt = 34, Y = ust + s.length * satirY + alt;
  const sol = 168, sag = 92, xBas = sol, xSon = G - sag;
  const enB = Math.max(...s.map((c) => Math.max(c.npv_p90, c.npv_tl))) * 1.05;
  const enK = Math.min(0, ...s.map((c) => c.npv_p10));
  const x = (v) => xBas + ((v - enK) / (enB - enK)) * (xSon - xBas);
  const svg = el("svg", { viewBox: `0 0 ${G} ${Y}`, role: "img", "aria-label": "Her koşulda öncelikli çatılar grafiği" });

  const izgara = el("g", { class: "g-izgara" }), eksen = el("g", { class: "g-eksen" });
  const adim = adimSec((enB - enK) / 1e6, 4);
  for (let v = 0; v <= enB / 1e6; v += adim) {
    izgara.append(el("line", { x1: x(v * 1e6), x2: x(v * 1e6), y1: ust, y2: Y - alt }));
    eksen.append(el("text", { x: x(v * 1e6), y: Y - alt + 15, "text-anchor": "middle" }, tr(v)));
  }
  eksen.append(el("text", { x: (xBas + xSon) / 2, y: Y - 4, "text-anchor": "middle" }, "Net bugünkü değer (milyon TL)"));
  eksen.append(el("text", { x: G - 4, y: Y - alt + 15, "text-anchor": "end" }, "kalma oranı"));
  svg.append(izgara, eksen);

  s.forEach((c, i) => {
    const yy = ust + i * satirY + satirY / 2;
    const oran = oranAl(c);
    const g = el("g", { class: "saglam-satir" });
    g.append(el("rect", { class: "saglam-zemin", x: 0, y: yy - satirY / 2, width: G, height: satirY, fill: "transparent" }));
    const isim = adi(c);
    g.append(el("text", { x: 0, y: yy + 4, class: "g-etiket-soluk" }, `${siraAl(c)}.`));
    g.append(el("text", { x: 22, y: yy + 4, class: "g-etiket-metin", style: "font-weight:500" }, isim.length > 22 ? isim.slice(0, 21) + "…" : isim));
    g.append(el("rect", { x: x(c.npv_p10), y: yy - 4, width: Math.max(2, x(c.npv_p90) - x(c.npv_p10)), height: 8, rx: 4, fill: "#fdba74" }));
    g.append(el("circle", { cx: x(c.npv_tl), cy: yy, r: 4.5, fill: "#c2410c", stroke: "#fff", "stroke-width": 2 }));
    // kalma orani: ince olcer + yuzde
    g.append(el("rect", { x: xSon + 18, y: yy - 3, width: 36, height: 6, rx: 3, fill: "#e2e8f0" }));
    g.append(el("rect", { x: xSon + 18, y: yy - 3, width: 36 * oran, height: 6, rx: 3, fill: "#0f172a" }));
    g.append(el("text", { x: G - 4, y: yy + 4, "text-anchor": "end", class: "g-etiket-metin" }, `%${Math.round(oran * 100)}`));
    g.addEventListener("mousemove", (e) => ipucuGoster(e,
      `<b>${kacis(isim)}</b><br>Hesaplanan NPV ${tl(c.npv_tl)}<br>Olası aralık ${aralikYazi(c.npv_p10, c.npv_p90)}<br>` +
      `${ORAN_KISA[analizGrup] || ORAN_KISA[""]} kalma: %${Math.round(oran * 100)}<br><span style="opacity:.7">Tıklayınca haritada açılır</span>`));
    g.addEventListener("mouseleave", ipucuGizle);
    g.addEventListener("click", () => { ipucuGizle(); haritayaGit(() => catiSec(c.cati_id, true)); });
    svg.append(g);
  });
  kap.replaceChildren(svg);
}

// ---- asistan (chatbot) ---------------------------------------------
// Soru /api/sohbet'e gider; Gemini gerekirse veritabanini salt okunur kullaniciyla sorgular.
// Cevapta adi gecen catilar yandaki haritada vurgulanir.
const HAZIR_SORULAR = [
  "Sanayide en öncelikli 10 çatı hangileri?",
  "Kamu binalarında en öncelikli 10 çatı hangileri?",
  "500 milyon TL bütçeyle hangi çatılar yapılabilir?",
  "Her koşulda öncelikli sanayi çatıları hangileri?",
  "Kurulan kWp başına en çok getiri sağlayan çatılar hangileri?",
  "Atatürk OSB'nin toplam potansiyeli ne kadar?",
  "Sanayi ve kamu binalarını karşılaştırır mısın?",
  "Mevcut GES'i olan en büyük çatılar hangileri?",
  "Yapay zekâ yorumu olan çatılar hangileri?",
];

// -- asistanin haritasi: cevaptaki catilari gormek icin yukari cikmak gerekmez
const sHarita = L.map("sorgu-harita", { zoomControl: false, zoomSnap: 0.5, scrollWheelZoom: false, attributionControl: false });
L.control.zoom({ position: "topright" }).addTo(sHarita);
L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
  maxZoom: 20, maxNativeZoom: 19,
}).addTo(sHarita);
sHarita.getContainer().classList.add("uydu-koyu");
sHarita.on("click focus", () => sHarita.scrollWheelZoom.enable());
document.getElementById("sorgu-harita").addEventListener("mouseleave", () => sHarita.scrollWheelZoom.disable());
let sSonuc = new Set();
let sSecili = null;
const sKatman = new Map(); // cati_id -> { poligon, nokta, p }
let sPoligon = null, sNokta = null;

function sStil(p, nokta) {
  const icinde = sSonuc.has(p.cati_id), secili = p.cati_id === sSecili;
  const s = {
    color: secili ? "#ffffff" : icinde ? SECIM_RENK : "#ffffff",
    weight: secili ? 3 : icinde ? 1.8 : 0.4,
    opacity: icinde || secili ? 1 : 0.3,
    fillColor: renk(p),
    fillOpacity: icinde || secili ? 0.9 : 0.12,
  };
  if (nokta) s.radius = icinde || secili ? Math.max(4, yaricap(p)) : 2.5;
  return s;
}

function sorguHaritasiKur() {
  sPoligon = L.featureGroup();
  sNokta = L.featureGroup();
  L.geoJSON(tumVeri).eachLayer((g) => {
    const p = g.feature.properties;
    g.setStyle(sStil(p, false));
    const n = L.circleMarker(g.getBounds().getCenter(), sStil(p, true));
    for (const k of [g, n]) {
      k.bindTooltip(ipucu(p), { sticky: true, className: "ipucu", direction: "top", offset: [0, -10] });
      k.on("click", () => asistanCatiSec(p.cati_id));
    }
    sPoligon.addLayer(g);
    sNokta.addLayer(n);
    sKatman.set(p.cati_id, { poligon: g, nokta: n, p });
  });
  sHarita.fitBounds(catiSiniri, { padding: [20, 20] });
  sHarita.setMaxBounds(catiSiniri.pad(0.12));
  sHarita.setMinZoom(sHarita.getZoom());
  sHarita.on("zoomend", sGorunum);
  sGorunum();
}

function sGorunum() {
  const yakin = sHarita.getZoom() >= POLIGON_ESIGI;
  const [goster, gizle] = yakin ? [sPoligon, sNokta] : [sNokta, sPoligon];
  if (sHarita.hasLayer(gizle)) sHarita.removeLayer(gizle);
  if (!sHarita.hasLayer(goster)) goster.addTo(sHarita);
  sKatman.forEach(({ poligon, nokta, p }) => {
    poligon.setStyle(sStil(p, false));
    nokta.setStyle(sStil(p, true));
    if (sSonuc.has(p.cati_id) || p.cati_id === sSecili) { poligon.bringToFront(); nokta.bringToFront(); }
  });
}

function sorguHaritasiGoster(idler) {
  sSonuc = new Set(idler);
  sSecili = null;
  document.getElementById("sorgu-harita-bos").hidden = sSonuc.size > 0;
  aDetayKapat();
  sGorunum();
  const sinir = L.latLngBounds([]);
  sSonuc.forEach((id) => { const k = sKatman.get(id); if (k) sinir.extend(k.poligon.getBounds()); });
  if (sinir.isValid()) sHarita.flyToBounds(sinir, { padding: [40, 40], maxZoom: 17, duration: 0.7 });
  else sHarita.flyToBounds(catiSiniri, { padding: [20, 20], duration: 0.7 });
}

// cevaptaki bir cati etiketine ya da haritadaki catiya tiklaninca: kart asistan haritasinin icinde acilir
const sHaritaKap = document.getElementById("sorgu-harita").parentElement;
const aDetay = document.getElementById("a-detay");
const aDetayIcerik = document.getElementById("a-detay-icerik");

async function asistanCatiSec(id) {
  sSecili = id;
  sGorunum();
  aDetay.hidden = false;
  sHaritaKap.classList.add("detay-acik");
  aDetay.scrollTop = 0;
  const k = sKatman.get(id);
  if (k) {
    const ayar = telefon()
      ? { paddingTopLeft: [20, 40], paddingBottomRight: [20, sHaritaKap.clientHeight * 0.6 + 20] }
      : { paddingTopLeft: [30, 40], paddingBottomRight: [DETAY_GENISLIK + 30, 40] };
    sHarita.flyToBounds(k.poligon.getBounds(), { ...ayar, maxZoom: 18, duration: 0.7 });
  }
  document.querySelectorAll(".cevap-cati").forEach((b) => b.classList.toggle("secili", Number(b.dataset.id) === id));
  aDetayIcerik.innerHTML = `<div class="d-ust"><p class="d-alt">Yükleniyor…</p></div>`;
  try {
    const c = await getir("/api/catilar/" + id);
    if (sSecili === id) {
      aDetay.style.setProperty("--d-renk", renk(c));
      aDetayIcerik.innerHTML = kartHtml(c);
    }
  } catch (e) {
    aDetayIcerik.innerHTML = `<div class="d-ust"><p class="d-alt">Bilgi alınamadı: ${kacis(e.message)}</p></div>`;
  }
}

function aDetayKapat() {
  aDetay.hidden = true;
  sHaritaKap.classList.remove("detay-acik");
  if (sSecili !== null) { sSecili = null; sGorunum(); }
  document.querySelectorAll(".cevap-cati").forEach((b) => b.classList.remove("secili"));
}
document.getElementById("a-detay-kapat").addEventListener("click", aDetayKapat);

// -- sohbet
const sohbetKutu = document.getElementById("sohbet-mesajlar");
const sohbetForm = document.getElementById("sohbet-form");
const sohbetGirdi = document.getElementById("sohbet-girdi");
const sohbetGonder = document.getElementById("sohbet-gonder");
const sohbetGecmis = []; // {rol, metin}

document.getElementById("hazir-sorular").innerHTML = HAZIR_SORULAR
  .map((s) => `<button type="button" class="hazir-soru">${kacis(s)}</button>`).join("");
document.querySelectorAll(".hazir-soru").forEach((b) => b.addEventListener("click", () => soruGonder(b.textContent)));

// cevap metnini guvenli bicimde HTML'e cevirir: **kalin**, "- " maddeler, satir sonlari
function cevapHtml(metin) {
  const satirlar = kacis(metin).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").split(/\n+/);
  let h = "", liste = false;
  for (const s of satirlar) {
    const madde = s.match(/^\s*[-*•]\s+(.*)$/);
    if (madde) { if (!liste) { h += "<ul>"; liste = true; } h += `<li>${madde[1]}</li>`; }
    else { if (liste) { h += "</ul>"; liste = false; } if (s.trim()) h += `<p>${s}</p>`; }
  }
  return h + (liste ? "</ul>" : "");
}

function mesajEkle(rol, html) {
  const el = document.createElement("div");
  el.className = "mesaj " + rol;
  el.innerHTML = html;
  sohbetKutu.append(el);
  sohbetKutu.scrollTop = sohbetKutu.scrollHeight;
  return el;
}

async function soruGonder(soru) {
  soru = soru.trim();
  if (!soru || sohbetGonder.disabled) return;
  sohbetGirdi.value = "";
  mesajEkle("kullanici", `<p>${kacis(soru)}</p>`);
  sohbetGecmis.push({ rol: "kullanici", metin: soru });
  const bekleyen = mesajEkle("asistan bekliyor", `<span class="nokta"></span><span class="nokta"></span><span class="nokta"></span>`);
  sohbetGonder.disabled = true;
  try {
    const r = await fetch("/api/sohbet", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mesajlar: sohbetGecmis }),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || r.status);
    sohbetGecmis.push({ rol: "asistan", metin: d.cevap });
    let html = cevapHtml(d.cevap);
    if (d.cati_idler.length) {
      const gosterilen = d.cati_idler.slice(0, 30);
      html += `<div class="cevap-catilar"><span>Haritada ${tr(d.cati_idler.length)} çatı:</span>${gosterilen
        .map((id) => `<button type="button" class="cevap-cati" data-id="${id}">${id}</button>`).join("")}${
        d.cati_idler.length > 30 ? `<span>+${d.cati_idler.length - 30}</span>` : ""}</div>`;
    }
    bekleyen.className = "mesaj asistan";
    bekleyen.innerHTML = html;
    bekleyen.querySelectorAll(".cevap-cati").forEach((b) => b.addEventListener("click", () => asistanCatiSec(Number(b.dataset.id))));
    sorguHaritasiGoster(d.cati_idler);
    // ana haritada da sessizce vurgulanir
    if (d.cati_idler.length) {
      vurgu = new Set(d.cati_idler);
      if (durum.grup || !durum.gesGoster) filtreUygula("", true);
      stilleriYenile();
      document.getElementById("vurgu-cip").hidden = false;
      document.getElementById("vurgu-yazi").innerHTML = `Asistan · <b>${tr(d.cati_idler.length)}</b> çatı`;
    }
  } catch (e) {
    sohbetGecmis.pop(); // cevapsiz soru gecmise girmesin
    bekleyen.className = "mesaj asistan hata";
    bekleyen.innerHTML = `<p>${kacis(e.message)}</p>`;
  } finally {
    sohbetGonder.disabled = false;
    sohbetKutu.scrollTop = sohbetKutu.scrollHeight;
  }
}

sohbetForm.addEventListener("submit", (e) => { e.preventDefault(); soruGonder(sohbetGirdi.value); });
sohbetGirdi.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); soruGonder(sohbetGirdi.value); }
});
document.getElementById("sohbet-temizle").addEventListener("click", () => {
  sohbetGecmis.length = 0;
  sohbetKutu.innerHTML = "";
  karsilamaEkle();
  sorguHaritasiGoster([]);
  if (vurgu) vurguAyarla(null);
});
// karsilama, sohbetin basinda normal bir asistan mesaji olarak durur (soru sorulunca kaybolmaz)
function karsilamaEkle() {
  mesajEkle("asistan", `<p>Merhaba! Çatıların güneş enerjisi potansiyeli, yatırım önceliği ve 10.000 senaryo testi
    hakkında soru sorabilirsiniz. Cevaplarım yalnızca projenin veritabanına dayanır; adı geçen çatıları yandaki
    haritada gösteririm.</p><p>Aşağıdaki hazır sorulardan birini seçerek de başlayabilirsiniz.</p>`);
}
karsilamaEkle();

// ---- menude bulunulan bolumu isaretle ------------------------------
const menuBaglanti = [...document.querySelectorAll("#menu-baglanti a")];
const bolumGozcu = new IntersectionObserver((girdiler) => {
  girdiler.forEach((g) => {
    if (!g.isIntersecting) return;
    menuBaglanti.forEach((a) => a.classList.toggle("aktif", a.getAttribute("href") === "#" + g.target.id));
  });
}, { rootMargin: "-45% 0px -50% 0px" });
document.querySelectorAll("main > section").forEach((s) => bolumGozcu.observe(s));

// ---- baslangic ------------------------------------------------------
function acilisiKapat() {
  const a = document.getElementById("acilis");
  a.classList.add("bitti");
  setTimeout(() => a.remove(), 700);
}

async function baslat() {
  const enAz = new Promise((r) => setTimeout(r, 900)); // acilis ekrani bir an gorunsun
  lejantCiz();
  altlikSec("uydu");
  const [bolgeler, catilar, ozet, analiz] = await Promise.all([
    getir("/api/bolgeler"), getir("/api/catilar"), getir("/api/ozet"), getir("/api/analiz"),
  ]);
  ozetVeri = ozet;
  tumVeri = catilar;
  analizVeri = analiz;
  bolgeleriCiz(bolgeler);
  catilariCiz();
  haritayiSinirla();
  sigdir(cekirdekSinir(), false, 16);
  girisGostergeleri();
  aracOzeti();
  listeCiz();
  analiziCiz();
  sorguHaritasiKur();
  const t = ozet.toplam;
  document.getElementById("veri-etiket").textContent =
    `Veri: ${tr(t.cati)} çatı · ${tr(t.potansiyelli_cati)} çatıda potansiyel · ${tr(t.mevcut_ges_cati)} çatıda mevcut GES · ${TARAMA_AD[t.tarama] || t.tarama}`;
  await enAz;
  acilisiKapat();
}

baslat().catch((e) => {
  console.error(e);
  const a = document.getElementById("acilis");
  a.querySelector(".acilis-alt").textContent = "Veriler yüklenemedi: " + e.message;
  a.querySelector(".acilis-cubuk")?.remove();
});
