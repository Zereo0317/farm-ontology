import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ButtonLink, buttonClass } from "@/components/button";
import { BriefingForm, WaitlistForm } from "@/components/intent-forms";
import { useCopy, useLocale } from "@/components/locale-context";
import { LiveLedgerCard } from "@/components/live-ledger";
import type { LiveLedger } from "@/lib/live.functions";
import type { Locale } from "@/lib/locale";
import { VISION, type Audience } from "@/lib/vision";

const HERO_IMAGE = "/photos/seges-hokkaido-dawn.jpg";

const INSTITUTION_COPY: Record<
  Locale,
  {
    eyebrow: string;
    title: string;
    deck: string;
    cta: string;
    end: string;
  }
> = {
  "zh-TW": {
    eyebrow: "資料治理 · 農業研究 · 機構合作",
    title: "可查證的農地資料，從來源、尺度到授權，一次看清。",
    deck: "檢視田間資料的來源、時間、空間尺度與使用條件。",
    cta: "預約機構簡報",
    end: "讓農業研究與治理決策，建立在可追溯的資料上。",
  },
  "zh-CN": {
    eyebrow: "数据治理 · 农业研究 · 机构合作",
    title: "可查证的农地数据，从来源、尺度到授权，一次看清。",
    deck: "查看田间数据的来源、时间、空间尺度与使用条件。",
    cta: "预约机构简报",
    end: "让农业研究与治理决策，建立在可追溯的数据上。",
  },
  en: {
    eyebrow: "DATA GOVERNANCE · AGRICULTURAL RESEARCH · INSTITUTIONAL PARTNERSHIPS",
    title: "Field data you can inspect, from source and scale to licence.",
    deck: "Explore field records by source, timing, spatial support, and permitted use.",
    cta: "Request an institutional briefing",
    end: "Ground agricultural research and governance in traceable records.",
  },
  ja: {
    eyebrow: "データガバナンス · 農業研究 · 機関連携",
    title: "出典、空間的な範囲、利用条件まで確認できる農地データ。",
    deck: "圃場データの出典、時点、空間的な範囲、利用条件をご覧いただけます。",
    cta: "機関向け説明を依頼",
    end: "追跡可能な記録を、農業研究とガバナンスの基盤に。",
  },
  th: {
    eyebrow: "ธรรมาภิบาลข้อมูล · วิจัยเกษตร · ความร่วมมือองค์กร",
    title: "ข้อมูลแปลงที่ตรวจสอบได้ ตั้งแต่แหล่งที่มา ขอบเขต จนถึงสิทธิ์ใช้งาน",
    deck: "ตรวจสอบแหล่งที่มา เวลา ขอบเขตเชิงพื้นที่ และเงื่อนไขการใช้ของข้อมูลแปลง",
    cta: "ขอรับฟังการบรรยายสำหรับองค์กร",
    end: "วางรากฐานงานวิจัยและธรรมาภิบาลเกษตรบนบันทึกที่ตรวจสอบย้อนกลับได้",
  },
};

const FINANCE_THESIS: Record<Locale, { title: string; deck: string; rails: [string, string][] }> = {
  "zh-TW": {
    title: "農業金融套利，從田間資訊優勢開始",
    deck: "我們研究以多來源農業資料支援自營農產品避險與市場套利。每筆訊號保留來源、時點、空間尺度與授權條件。",
    rails: [
      ["資料時點", "記錄發布與取得時間。"],
      ["原生尺度", "格網資料與田區觀測分開。"],
      ["使用權限", "依來源與授權用途評估。"],
    ],
  },
  "zh-CN": {
    title: "农业金融套利，从田间信息优势开始",
    deck: "我们研究以多来源农业数据支持自营农产品套期保值与市场套利。每条信号保留来源、时点、空间尺度与授权条件。",
    rails: [
      ["数据时点", "记录发布时间与获取时间。"],
      ["原生尺度", "网格数据与田块观测分开。"],
      ["使用权限", "按来源与授权用途评估。"],
    ],
  },
  en: {
    title: "Farm finance arbitrage starts with traceable field information.",
    deck: "We study own-account agricultural hedging and market arbitrage using multi-source field data with recorded timing, spatial support, and licence conditions.",
    rails: [
      ["Data timing", "Publication and acquisition time."],
      ["Native scale", "Grid data kept distinct from field observations."],
      ["Use rights", "Source and permitted purpose."],
    ],
  },
  ja: {
    title: "農業金融アービトラージは、追跡可能な圃場情報から。",
    deck: "複数の圃場データを用いて、自社勘定の農産物ヘッジと市場アービトラージを研究します。各データの時点、空間的な範囲、利用条件を記録します。",
    rails: [
      ["データ時点", "公開時刻と取得時刻。"],
      ["固有の範囲", "格子データと圃場観測を区別。"],
      ["利用権", "出典と許諾された用途。"],
    ],
  },
  th: {
    title: "อาร์บิทราจการเงินเกษตร เริ่มจากข้อมูลแปลงที่ตรวจสอบย้อนกลับได้",
    deck: "เราศึกษาการป้องกันความเสี่ยงและอาร์บิทราจสินค้าเกษตรในบัญชีของบริษัท โดยใช้ข้อมูลหลายแหล่งที่ระบุเวลา ขอบเขตเชิงพื้นที่ และเงื่อนไขใบอนุญาต",
    rails: [
      ["เวลาของข้อมูล", "เวลาที่เผยแพร่และได้รับ"],
      ["ขอบเขตดั้งเดิม", "แยกข้อมูลกริดจากข้อมูลแปลง"],
      ["สิทธิ์ใช้งาน", "แหล่งข้อมูลและวัตถุประสงค์ที่อนุญาต"],
    ],
  },
};

export function LandingPage({ ledger, audience }: { ledger: LiveLedger; audience: Audience }) {
  const copy = useCopy();
  const locale = useLocale();
  const vision = VISION[locale];
  const institution = INSTITUTION_COPY[locale];
  const [showBar, setShowBar] = useState(false);
  const [formVisible, setFormVisible] = useState(false);
  const title = audience === "farmer" ? copy.hero.title : institution.title;
  const deck = audience === "farmer" ? copy.hero.deck : institution.deck;
  const cta = audience === "farmer" ? copy.hero.primary : institution.cta;
  const deviceNote =
    locale === "zh-TW"
      ? "第一筆記錄保存在這台裝置，不會寫入正式帳本。"
      : locale === "zh-CN"
        ? "第一笔记录保存在这台设备，不会写入正式账本。"
        : locale === "ja"
          ? "最初の記録はこの端末に保存され、正式な台帳には書き込まれません。"
          : locale === "th"
            ? "บันทึกแรกจะเก็บไว้ในอุปกรณ์นี้ และยังไม่ถูกเขียนลงบัญชีจริง"
            : "Your first record stays on this device; it is not written to the production ledger.";
  const ctaAction =
    audience === "farmer" ? (
      <ButtonLink to="/$locale/start" params={{ locale }}>
        {cta}
      </ButtonLink>
    ) : (
      <a href="#live" className={buttonClass()}>
        {cta}
      </a>
    );
  const principles =
    locale === "zh-TW"
      ? [
          ["空間支援", "每筆讀值都說明代表多大範圍。格網資料不冒充單一田區。"],
          ["來源與時點", "保留發布者、知道時間與生效時間，讓數字可以回頭查。"],
          ["授權與缺口", "條款不明就標出缺口；需要人工判斷時，流程停下來等確認。"],
        ]
      : locale === "zh-CN"
        ? [
            ["空间支持", "每笔读值都说明代表多大范围。格网数据不冒充单一田块。"],
            ["来源与时点", "保留发布者、获知时间与生效时间，让数字可以回查。"],
            ["授权与缺口", "条款不明就标出缺口；需要人工判断时，流程停下来等确认。"],
          ]
        : locale === "ja"
          ? [
              [
                "空間的な範囲",
                "数値がどの範囲を表すかを記録。格子データを圃場の値とは扱いません。",
              ],
              ["出典と時点", "発表元、把握した時刻、有効時刻を残し、後から確認できます。"],
              [
                "利用条件と欠損",
                "条件が不明なら欠損として示し、人の判断が必要なら確認を待ちます。",
              ],
            ]
          : locale === "th"
            ? [
                [
                  "ขอบเขตเชิงพื้นที่",
                  "ระบุทุกครั้งว่าค่าครอบคลุมพื้นที่ใด ข้อมูลกริดไม่ถูกอ้างว่าเป็นค่าของแปลงเดียว",
                ],
                [
                  "แหล่งที่มาและเวลา",
                  "เก็บผู้เผยแพร่ เวลาที่ทราบ และเวลาที่มีผล เพื่อให้ตรวจสอบย้อนหลังได้",
                ],
                [
                  "สิทธิ์และช่องว่าง",
                  "เงื่อนไขไม่ชัดเจนจะแสดงเป็นช่องว่าง และหยุดรอเมื่อจำเป็นต้องให้คนตัดสินใจ",
                ],
              ]
            : [
                [
                  "Spatial support",
                  "Each reading says what area it represents. Grid data is never presented as a single plot measurement.",
                ],
                [
                  "Source and time",
                  "Publisher, time known, and effective time stay attached so a value can be checked later.",
                ],
                [
                  "Licence and gaps",
                  "Unclear terms stay visible as a gap. The flow pauses when a human decision is required.",
                ],
              ];
  const principlesTitle =
    locale === "zh-TW"
      ? "田間資料，先把邊界說清楚"
      : locale === "zh-CN"
        ? "田间数据，先把边界说清楚"
        : locale === "ja"
          ? "圃場データの前提を明確に"
          : locale === "th"
            ? "ระบุขอบเขตของข้อมูลแปลงให้ชัดเจน"
            : "Field data, with its limits in plain view";
  const principlesDeck =
    locale === "zh-TW"
      ? "先看空間範圍、來源時間與使用條件，再判讀每一筆農地觀測。"
      : locale === "zh-CN"
        ? "先看空间范围、来源时间与使用条件，再判读每一笔农地观测。"
        : locale === "ja"
          ? "空間的な範囲、出典と時点、利用条件を確認してから圃場データを読み解きます。"
          : locale === "th"
            ? "ตรวจสอบขอบเขต แหล่งที่มา เวลา และเงื่อนไขการใช้ ก่อนอ่านข้อมูลแต่ละรายการ"
            : "Read each field observation with its spatial scope, source, timing, and use conditions in view.";

  useEffect(() => {
    const target = document.getElementById("hero-cta");
    if (!target) return;
    const observer = new IntersectionObserver(
      ([entry]) => setShowBar(entry.boundingClientRect.bottom < 0),
      { threshold: [0, 1] },
    );
    observer.observe(target);
    const form = document.getElementById("live");
    let formObserver: IntersectionObserver | undefined;
    if (form) {
      formObserver = new IntersectionObserver(([e]) => setFormVisible(e.isIntersecting), {
        threshold: [0, 0.15],
      });
      formObserver.observe(form);
    }
    return () => {
      observer.disconnect();
      formObserver?.disconnect();
    };
  }, [audience]);

  return (
    <div className="pb-24 md:pb-0">
      <section className="hero-editorial">
        <figure className="hero-editorial-photo" aria-hidden="true">
          <img src={HERO_IMAGE} alt="" fetchPriority="high" />
        </figure>
        <div className="hero-editorial-copy">
          <div role="tablist" aria-label={vision.switchLabel} className="audience-switch">
            {(["farmer", "research"] as const).map((key) => {
              const selected = audience === key;
              return (
                <Link
                  key={key}
                  to="/$locale"
                  params={{ locale }}
                  search={{ for: key }}
                  role="tab"
                  aria-selected={selected}
                  className={`audience-option ${selected ? "is-selected" : ""}`}
                >
                  {key === "farmer" ? vision.farmer : vision.research}
                </Link>
              );
            })}
          </div>
          <h1 className="text-hero mt-5 max-w-xl font-display text-balance">{title}</h1>
          <p className="mt-5 max-w-lg text-lg leading-relaxed text-muted">{deck}</p>
          <div id="hero-cta" className="mt-6">
            {ctaAction}
            {audience === "farmer" && <p className="mt-3 text-sm text-muted">{copy.hero.noCard}</p>}
            {audience === "farmer" && (
              <p className="mt-1 max-w-md text-xs leading-relaxed text-muted">{deviceNote}</p>
            )}
          </div>
        </div>
      </section>

      <section className="border-t border-line">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 md:py-20">
          <h2 className="font-display text-3xl leading-tight sm:text-4xl">{copy.pains.title}</h2>
          <p className="mt-3 max-w-2xl text-lg text-muted">{copy.pains.lede}</p>
          <div className="mt-8 grid gap-4 md:grid-cols-2">
            {copy.pains.items.map((item, index) => (
              <article key={index} className={`rise rise-${index + 1} editorial-card p-5 sm:p-6`}>
                <h3 className="font-display text-xl leading-snug">{item.split(/[:：]/)[0]}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">
                  {item.substring(item.search(/[:：]/) + 1)}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="flow" className="finance-editorial scroll-mt-nav border-t border-line">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 md:py-20">
          <div className="finance-intro">
            <h2 className="font-display text-3xl leading-tight sm:text-4xl">
              {FINANCE_THESIS[locale].title}
            </h2>
            <p className="mt-4 max-w-2xl text-lg leading-relaxed">{FINANCE_THESIS[locale].deck}</p>
          </div>
          <div className="finance-rails">
            {FINANCE_THESIS[locale].rails.map(([heading, body]) => (
              <article key={heading}>
                <h3>{heading}</h3>
                <p>{body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-line">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 md:py-20">
          <h2 className="font-display text-3xl leading-tight sm:text-4xl">{principlesTitle}</h2>
          <p className="mt-3 max-w-2xl text-lg leading-relaxed">{principlesDeck}</p>
          <div className="field-principles mt-8">
            {principles.map(([heading, body], index) => (
              <article key={heading} className="principle-item">
                <span className="principle-index">0{index + 1}</span>
                <h3>{heading}</h3>
                <p>{body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="live" className="scroll-mt-nav border-t border-line">
        <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6">
          <div className="max-w-xl">
            {audience === "farmer" ? <WaitlistForm /> : <BriefingForm />}
          </div>
          <details className="group mt-12">
            <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-4 font-display text-2xl">
              {vision.openLedger}
              <span aria-hidden className="text-muted">
                +
              </span>
            </summary>
            <div className="pt-6">
              <LiveLedgerCard initial={ledger} />
            </div>
          </details>
        </div>
      </section>

      <section className="bg-ink text-on-ink">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-start gap-6 px-4 py-16 sm:px-6">
          <h2 className="max-w-3xl font-display text-3xl leading-tight sm:text-5xl">
            {audience === "farmer" ? copy.hero.lead : institution.end}
          </h2>
          {audience === "farmer" ? (
            <ButtonLink to="/$locale/start" params={{ locale }} variant="inverse">
              {cta}
            </ButtonLink>
          ) : (
            <a href="#live" className={buttonClass("inverse")}>
              {cta}
            </a>
          )}
        </div>
      </section>

      {showBar && !formVisible ? (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-paper p-3 md:hidden">
          {audience === "farmer" ? (
            <ButtonLink to="/$locale/start" params={{ locale }} className="w-full">
              {cta}
            </ButtonLink>
          ) : (
            <a href="#live" className={buttonClass("primary", "w-full")}>
              {cta}
            </a>
          )}
        </div>
      ) : null}
    </div>
  );
}
