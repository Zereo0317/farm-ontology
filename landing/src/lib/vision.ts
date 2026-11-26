import type { Locale } from "@/lib/locale";

export type Audience = "farmer" | "research" | "finance";

export type Vision = {
  farmer: string;
  research: string;
  finance: string;
  switchLabel: string;
  navFlow: string;
  openLedger: string;
  researchCta: string;
  financeCta: string;
};

export const VISION: Record<Locale, Vision> = {
  "zh-TW": {
    farmer: "農場經營者",
    research: "研究與機構",
    finance: "農業金融研究",
    switchLabel: "選擇閱讀對象",
    navFlow: "農業金融套利",
    openLedger: "查看即時田間帳本",
    researchCta: "索取機構簡報",
    financeCta: "農業金融研究簡報",
  },
  "zh-CN": {
    farmer: "农场经营者",
    research: "研究与机构",
    finance: "农业金融研究",
    switchLabel: "选择阅读对象",
    navFlow: "农业金融套利",
    openLedger: "查看实时田间账本",
    researchCta: "索取机构简报",
    financeCta: "农业金融研究简报",
  },
  en: {
    farmer: "For farmers",
    research: "Research & institutions",
    finance: "Farm finance research",
    switchLabel: "Choose your audience",
    navFlow: "Farm finance arbitrage",
    openLedger: "View the live field ledger",
    researchCta: "Research briefing",
    financeCta: "Finance briefing",
  },
  ja: {
    farmer: "農業経営者",
    research: "研究・機関向け",
    finance: "農業金融研究",
    switchLabel: "対象を選択",
    navFlow: "農業金融アービトラージ",
    openLedger: "圃場台帳を表示",
    researchCta: "機関向け説明",
    financeCta: "金融研究の説明",
  },
  th: {
    farmer: "เกษตรกร",
    research: "งานวิจัยและองค์กร",
    finance: "งานวิจัยการเงินเกษตร",
    switchLabel: "เลือกกลุ่มผู้อ่าน",
    navFlow: "อาร์บิทราจการเงินเกษตร",
    openLedger: "ดูบัญชีข้อมูลแปลงสด",
    researchCta: "สรุปข้อมูลองค์กร",
    financeCta: "สรุปวิจัยการเงินเกษตร",
  },
};
