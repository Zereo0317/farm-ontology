import type { Audience } from "@/lib/vision";
import type { Locale } from "@/lib/locale";

type PreviewCopy = {
  title: string;
  description: string;
  imageAlt: string;
  imageWidth: number;
  imageHeight: number;
};

export const OG_LOCALE: Record<Locale, string> = {
  "zh-TW": "zh_TW",
  "zh-CN": "zh_CN",
  en: "en_US",
  ja: "ja_JP",
  th: "th_TH",
};

export const SOCIAL_PREVIEW: Record<Locale, Record<Audience, PreviewCopy>> = {
  "zh-TW": {
    farmer: {
      title: "田間紀錄，直接支援下一步判斷｜Seges",
      description: "在已授權的農場記錄田間觀察，並核對天氣、衛星資料、空間範圍與授權狀態。",
      imageAlt: "晨光中的蔬菜田與層疊丘陵",
      imageWidth: 1731,
      imageHeight: 909,
    },
    research: {
      title: "讓農業研究，從可追溯的田間資料開始｜Seges",
      description: "逐筆檢視來源、時間、空間支援與授權狀態，保留研究資料脈絡。",
      imageAlt: "晨光中的分區農田與丘陵景觀",
      imageWidth: 1672,
      imageHeight: 941,
    },
    finance: {
      title: "以可查證的田間資料支援農業金融研究｜Seges",
      description: "檢視農產品避險研究所需的資料來源、時間、空間範圍與授權條件。",
      imageAlt: "晨光中的分區農田與丘陵景觀",
      imageWidth: 1672,
      imageHeight: 941,
    },
  },
  "zh-CN": {
    farmer: {
      title: "农田记录，直接支持下一步决策｜Seges",
      description: "在已授权的农场记录田间观察，并核对天气、卫星数据、空间范围和授权状态。",
      imageAlt: "晨光中的水稻田与丘陵",
      imageWidth: 1672,
      imageHeight: 941,
    },
    research: {
      title: "让农业研究从可追溯的田间数据开始｜Seges",
      description: "逐条查看来源、时间、空间范围和授权状态，保留研究数据脉络。",
      imageAlt: "带有水渠的分区稻田景观",
      imageWidth: 1672,
      imageHeight: 941,
    },
    finance: {
      title: "用可查证的田间数据开展农业金融研究｜Seges",
      description: "核对农产品套期保值研究所需的数据来源、时间、空间范围和授权条件。",
      imageAlt: "带有水渠的分区稻田景观",
      imageWidth: 1672,
      imageHeight: 941,
    },
  },
  en: {
    farmer: {
      title: "Field records for the next farm decision | Seges",
      description: "For authorized farms, record field observations and review weather, satellite sources, spatial scope, and licence status.",
      imageAlt: "Soybean rows across a sunlit working farm",
      imageWidth: 1672,
      imageHeight: 941,
    },
    research: {
      title: "Traceable field data for agricultural research | Seges",
      description: "Review source, timing, spatial support and licence status together.",
      imageAlt: "Connected crop plots beside a natural waterway",
      imageWidth: 1672,
      imageHeight: 941,
    },
    finance: {
      title: "Traceable field data for farm-finance research | Seges",
      description: "Review source, timing, spatial support and licence conditions for agricultural hedging research.",
      imageAlt: "Connected crop plots beside a natural waterway",
      imageWidth: 1672,
      imageHeight: 941,
    },
  },
  ja: {
    farmer: {
      title: "次の判断につながる、圃場の記録｜Seges",
      description: "利用が許可された農場で観測を記録し、気象・衛星データ・空間範囲・利用条件を確認できます。",
      imageAlt: "朝日に照らされた畑と山並み",
      imageWidth: 1672,
      imageHeight: 941,
    },
    research: {
      title: "農業研究を、追跡できる圃場データから｜Seges",
      description: "出典・時刻・空間範囲・利用条件をまとめて確認できます。",
      imageAlt: "水路と研究区画が広がる農業景観",
      imageWidth: 1672,
      imageHeight: 941,
    },
    finance: {
      title: "検証できる圃場データから始める農業金融研究｜Seges",
      description: "農産物ヘッジ研究に向け、出典、時点、空間的な範囲、利用条件を確認します。",
      imageAlt: "水路と研究区画が広がる農業景観",
      imageWidth: 1672,
      imageHeight: 941,
    },
  },
  th: {
    farmer: {
      title: "บันทึกแปลง เพื่อการตัดสินใจครั้งต่อไป | Seges",
      description: "บันทึกสิ่งที่พบในฟาร์มที่ได้รับอนุญาต พร้อมตรวจดูอากาศ ข้อมูลดาวเทียม ขอบเขตพื้นที่ และสิทธิ์ใช้งาน",
      imageAlt: "นาข้าวและสวนผลไม้ในแสงยามเช้า",
      imageWidth: 1672,
      imageHeight: 941,
    },
    research: {
      title: "เริ่มงานวิจัยเกษตรจากข้อมูลแปลงที่ตรวจสอบย้อนกลับได้ | Seges",
      description: "ตรวจดูแหล่งที่มา เวลา ขอบเขตเชิงพื้นที่ และสถานะใบอนุญาตในบริบทเดียวกัน",
      imageAlt: "ผืนนาและทางน้ำในภูมิทัศน์เกษตร",
      imageWidth: 1672,
      imageHeight: 941,
    },
    finance: {
      title: "ข้อมูลแปลงที่ตรวจสอบได้ สำหรับงานวิจัยการเงินเกษตร | Seges",
      description: "ตรวจแหล่งที่มา เวลา ขอบเขตพื้นที่ และสิทธิ์ใช้งานสำหรับการศึกษาป้องกันความเสี่ยงสินค้าเกษตร",
      imageAlt: "ผืนนาและทางน้ำในภูมิทัศน์เกษตร",
      imageWidth: 1672,
      imageHeight: 941,
    },
  },
};

export function socialImage(locale: Locale, audience: Audience) {
  const audienceSlug = audience === "farmer" ? "farmer" : "research";
  return `https://seges.ai/og/og-${locale.toLowerCase()}-${audienceSlug}.jpg`;
}

export function socialMeta({
  title,
  description,
  image,
  imageAlt,
  imageWidth,
  imageHeight,
  url,
}: {
  title: string;
  description: string;
  image: string;
  imageAlt: string;
  imageWidth: number;
  imageHeight: number;
  url: string;
}) {
  return [
    { property: "og:title", content: title },
    { property: "og:description", content: description },
    { property: "og:url", content: url },
    { property: "og:image", content: image },
    { property: "og:image:alt", content: imageAlt },
    { property: "og:image:type", content: "image/jpeg" },
    { property: "og:image:width", content: String(imageWidth) },
    { property: "og:image:height", content: String(imageHeight) },
    { name: "twitter:card", content: "summary_large_image" },
    { name: "twitter:title", content: title },
    { name: "twitter:description", content: description },
    { name: "twitter:image", content: image },
    { name: "twitter:image:alt", content: imageAlt },
  ];
}
