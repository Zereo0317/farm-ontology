import type { Locale } from "@/lib/locale";

export type Audience = "farmer" | "research";

export type Vision = {
  farmer: string;
  research: string;
  switchLabel: string;
  navFlow: string;
  openLedger: string;
};

export const VISION: Record<Locale, Vision> = {
  "zh-TW": {
    farmer: "農場經營者",
    research: "研究與機構",
    switchLabel: "選擇閱讀對象",
    navFlow: "農業金融套利",
    openLedger: "查看即時田間帳本",
  },
  "zh-CN": {
    farmer: "农场经营者",
    research: "研究与机构",
    switchLabel: "选择阅读对象",
    navFlow: "农业金融套利",
    openLedger: "查看实时田间账本",
  },
  en: {
    farmer: "For farmers",
    research: "Research & institutions",
    switchLabel: "Choose your audience",
    navFlow: "Farm finance strategy",
    openLedger: "View the live field ledger",
  },
  ja: {
    farmer: "農業経営者",
    research: "研究・機関向け",
    switchLabel: "対象を選択",
    navFlow: "農業金融アービトラージ",
    openLedger: "圃場台帳を表示",
  },
  th: {
    farmer: "เกษตรกร",
    research: "งานวิจัยและองค์กร",
    switchLabel: "เลือกกลุ่มผู้อ่าน",
    navFlow: "อาร์บิทราจการเงินเกษตร",
    openLedger: "ดูบัญชีข้อมูลแปลงสด",
  },
};
