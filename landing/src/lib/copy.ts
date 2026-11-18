import type { PillarId } from "@/lib/copy-types";
import type { CopyBook } from "@/lib/copy-types";
import { en } from "@/lib/copy/en";
import { ja } from "@/lib/copy/ja";
import { th } from "@/lib/copy/th";
import { zhCN } from "@/lib/copy/zh-CN";
import { zhTW } from "@/lib/copy/zh-TW";

export const COPY: CopyBook = {
  "zh-TW": zhTW,
  "zh-CN": zhCN,
  en,
  ja,
  th,
};

export const PAIN_PILLAR: PillarId[] = ["A", "B", "B", "B", "C"];

export const LEDGER_URL = "https://farm-seges-ai-451400509859.asia-east1.run.app/farm";
