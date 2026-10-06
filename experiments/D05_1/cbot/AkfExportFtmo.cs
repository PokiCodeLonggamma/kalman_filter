// EXP-D05.1 — Export des données du compte FTMO depuis cTrader (cBot), sans Open API.
// Ne passe aucun ordre. Écrit dans Documents\cAlgo\Data\cBots\... (dossier autorisé sans droits étendus).
// Sorties : ftmo_symboles_liste.csv (tous les noms), ftmo_symboles_fiches.csv (fiche des symboles demandés),
//           ftmo_<nom>_m30.csv (bougies M30, UTC, ouverture), ftmo_<nom>_ticks.csv (bid/ask des derniers jours).
// Version 2 (2026-10-06) : fiche complète (type et jour triple du swap, commission, paliers de levier, séances) ;
//           bougies et ticks seulement pour la liste « Bougies et ticks pour » (vide : aucune).
// Version 3 (2026-10-06) : paramètres renommés (une instance garde la valeur d'un paramètre qui garde son nom de
//           propriété) ; fiche aussi pour chaque symbole de la liste des bougies ; SAN remplacé par META (porteur) ;
//           cryptos candidates au remplacement d'AVAX (porteur) ; AVAUSD gardé pour ses coûts.
using System;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using cAlgo.API;
using cAlgo.API.Internals;
using File = System.IO.File;   // cAlgo.API a aussi un type File : on désigne celui de .NET

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class AkfExportFtmo : Robot
    {
        [Parameter("Fiches v3 (séparés par ;)",
            DefaultValue = "US100.cash;US30.cash;GER40.cash;GBPJPY;USOIL.cash;UKOIL.cash;XAUUSD;META;BTCUSD;ETHUSD;SOLUSD;AVAUSD;XRPUSD")]
        public string Fiches { get; set; }

        [Parameter("Bougies et ticks v3 (séparés par ;)", DefaultValue = "META;AVAUSD;DOGEUSD;LNKUSD;AAVUSD;UNIUSD;XLMUSD")]
        public string Donnees { get; set; }

        [Parameter("Début des bougies (AAAA-MM-JJ)", DefaultValue = "2020-01-01")]
        public string Start { get; set; }

        [Parameter("Jours de ticks (écarts)", DefaultValue = 10, MinValue = 0, MaxValue = 60)]
        public int TickDays { get; set; }

        private static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

        protected override void OnStart()
        {
            var start = DateTime.SpecifyKind(DateTime.ParseExact(Start, "yyyy-MM-dd", Inv), DateTimeKind.Utc);
            File.WriteAllText("ftmo_symboles_liste.csv", "nom\n" + string.Join("\n", Symbols.OrderBy(s => s)) + "\n");

            var data = Donnees.Split(';').Select(s => s.Trim()).Where(s => s.Length > 0).ToList();
            var noms = Fiches.Split(';').Select(s => s.Trim()).Where(s => s.Length > 0).Concat(data).Distinct().ToList();
            var fiches = new StringBuilder("nom,description,base,cotation,digits,pip_size,tick_size,lot_size,volume_min_unites,pip_value,tick_value,"
                + "swap_type,swap_long,swap_short,swap_triple,frais_admin,commission_type,commission,commission_min_type,commission_min,"
                + "commission_min_devise,levier_paliers,seances,ecart_actuel\n");
            foreach (var name in noms)
            {
                if (!Symbols.Exists(name))
                {
                    Print("ABSENT : {0} (voir ftmo_symboles_liste.csv)", name);
                    continue;
                }
                var s = Symbols.GetSymbol(name);
                var paliers = string.Join("|", s.DynamicLeverage.Select(t => t.Volume.ToString(Inv) + ":" + t.Leverage.ToString(Inv)));
                var seances = string.Join("|", s.MarketHours.Sessions.Select(x => Jour(x.StartDay) + " " + Heure(x.StartTime) + "-" + Jour(x.EndDay) + " " + Heure(x.EndTime)));
                fiches.AppendFormat(Inv, "{0},\"{1}\",{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},\"{21}\",\"{22}\",{23}\n",
                    name, (s.Description ?? "").Replace("\"", "'"), s.BaseAsset?.Name, s.QuoteAsset?.Name, s.Digits, s.PipSize, s.TickSize,
                    s.LotSize, s.VolumeInUnitsMin, s.PipValue, s.TickValue, s.SwapCalculationType, s.SwapLong, s.SwapShort,
                    s.Swap3DaysRollover?.ToString() ?? "", s.AdministrativeCharge, s.CommissionType, s.Commission, s.MinCommissionType,
                    s.MinCommission, s.MinCommissionAsset?.Name, paliers, seances, s.Spread);
                Print("{0} : swap {1} {2}/{3} (triple {4}), commission {5} {6}, levier {7}", name, s.SwapCalculationType, s.SwapLong,
                    s.SwapShort, s.Swap3DaysRollover?.ToString() ?? "-", s.Commission, s.CommissionType, paliers);
                if (!data.Contains(name))
                    continue;
                ExportBars(name, start);
                if (TickDays > 0)
                    ExportTicks(name);
            }
            File.WriteAllText("ftmo_symboles_fiches.csv", fiches.ToString());
            Print("Terminé. Fichiers dans Documents\\cAlgo\\Data\\cBots.");
            Stop();
        }

        private void ExportBars(string name, DateTime start)
        {
            var bars = MarketData.GetBars(TimeFrame.Minute30, name);
            for (int k = 0; k < 5000 && bars.Count > 0 && bars.OpenTimes[0] > start; k++)
                if (bars.LoadMoreHistory() == 0)
                    break;
            var sb = new StringBuilder("time,open,high,low,close,tick_volume\n");
            int n = 0;
            for (int i = 0; i < bars.Count - 1; i++)          // dernière bougie en cours : exclue
            {
                var b = bars[i];
                if (b.OpenTime < start)
                    continue;
                sb.AppendFormat(Inv, "{0:yyyy-MM-ddTHH:mm:ssZ},{1},{2},{3},{4},{5}\n", b.OpenTime, b.Open, b.High, b.Low, b.Close, b.TickVolume);
                n++;
            }
            File.WriteAllText("ftmo_" + Clean(name) + "_m30.csv", sb.ToString());
            Print("{0} : {1} bougies M30, première disponible {2:yyyy-MM-dd HH:mm} UTC", name, n, bars.Count > 0 ? bars.OpenTimes[0] : DateTime.MinValue);
        }

        private void ExportTicks(string name)
        {
            var from = Server.Time.AddDays(-TickDays);
            var ticks = MarketData.GetTicks(name);
            for (int k = 0; k < 20000 && ticks.Count > 0 && ticks[0].Time > from; k++)
                if (ticks.LoadMoreHistory() == 0)
                    break;
            var sb = new StringBuilder("time,bid,ask\n");
            int n = 0;
            for (int i = 0; i < ticks.Count; i++)
            {
                var t = ticks[i];
                if (t.Time < from)
                    continue;
                sb.AppendFormat(Inv, "{0:yyyy-MM-ddTHH:mm:ss.fffZ},{1},{2}\n", t.Time, t.Bid, t.Ask);
                n++;
            }
            File.WriteAllText("ftmo_" + Clean(name) + "_ticks.csv", sb.ToString());
            Print("{0} : {1} ticks sur {2} jours", name, n, TickDays);
        }

        private static string Jour(DayOfWeek d)
        {
            return d.ToString().Substring(0, 3);
        }

        private static string Heure(TimeSpan t)
        {
            return string.Format(Inv, "{0:00}:{1:00}", (int)t.TotalHours, t.Minutes);
        }

        private static string Clean(string name)
        {
            return new string(name.Select(c => char.IsLetterOrDigit(c) ? char.ToLowerInvariant(c) : '_').ToArray());
        }
    }
}
