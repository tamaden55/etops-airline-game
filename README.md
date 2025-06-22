# ETOPS Airline Strategy ✈️

双発機の長距離飛行基準（ETOPS）をテーマにした教育ゲーム

## 🎯 ゲーム概要

航空会社の経営者として、限られた機材で10路線の国際ネットワークを構築するチャレンジゲームです。各路線でETOPS要件を判定し、機体性能と環境性を考慮した最適な運航判断を行います。

## 🛫 特徴

- **リアルなETOPS計算**: 実際の航空業界基準に基づく飛行制限判定
- **環境性評価**: CO₂排出量を考慮したサステナブル運航
- **教育要素**: 航空業界の専門知識を楽しく学習
- **10路線チャレンジ**: ランダム生成される多様な国際路線

## 🚀 クイックスタート

```bash
# リポジトリをクローン
git clone https://github.com/YOUR_USERNAME/etops-airline-game.git
cd etops-airline-game

# 依存ライブラリをインストール
pip install -r requirements.txt

# アプリを起動
streamlit run app.py
```

## 🎮 遊び方

1. **機材選択**: B787-9、A350-900、B737MAXから選択
2. **10路線チャレンジ**: ランダム生成される国際路線に挑戦
3. **ETOPS判定**: 各路線で必要なETOPS分数と機材性能を比較
4. **スコア獲得**: ETOPS適合性とCO₂効率でポイント獲得
5. **結果評価**: 合計スコアで最終評価

## 📊 採点システム

- ✅ ETOPS適合: +10点
- 🌱 低CO₂排出: +5〜10点  
- ❌ ETOPS不適合: -5点

## 🛠 技術スタック

- **Python 3.8+**
- **Streamlit**: Web UI フレームワーク
- **pandas**: データ処理
- **geopy**: 地理的距離計算

## 📁 プロジェクト構成

```
etops-airline-game/
├── app.py                 # メインアプリケーション
├── data/
│   ├── aircraft.csv       # 機材データ
│   └── airports.csv       # 空港データ
├── requirements.txt       # 依存ライブラリ
└── README.md             # このファイル
```

## 🔮 今後の予定

- [ ] 地図可視化（folium統合）
- [ ] 飛行アニメーション
- [ ] バッジ・称号システム
- [ ] 機材解放システム
- [ ] スコア保存機能
- [ ] より多くの機材・空港データ

## 🤝 コントリビューション

フィードバックや改善提案を歓迎します！

1. このリポジトリをFork
2. 機能ブランチを作成 (`git checkout -b feature/AmazingFeature`)
3. 変更をコミット (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにPush (`git push origin feature/AmazingFeature`)
5. Pull Requestを作成

## 📝 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## 🙏 謝辞

航空業界の専門知識と教育への貢献を目指して開発されました。

---

**🎓 教育目的**: このゲームは航空業界のETOPS規定について学習することを目的としており、実際の運航判断の参考にはしないでください。
