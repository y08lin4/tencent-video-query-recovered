package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"strings"
	"time"
)

const (
	api1URL = "https://data.video.qq.com/fcgi-bin/data"
	api2URL = "https://union.video.qq.com/fcgi-bin/data"
)

type coverInfo struct {
	CID        string   `json:"cid"`
	Title      string   `json:"title"`
	Type       string   `json:"type"`
	TypeName   string   `json:"type_name"`
	VideoIDs   []string `json:"video_ids"`
	PayStatus  string   `json:"pay_status"`
	CoverPicHz string   `json:"cover_pic_hz"`
	CoverPicVt string   `json:"cover_pic_vt"`
}

type videoDetail struct {
	VID             string         `json:"vid"`
	Title           string         `json:"title"`
	DurationSeconds string         `json:"duration_seconds"`
	Duration        string         `json:"duration"`
	URL             string         `json:"url"`
	CoverList       string         `json:"cover_list"`
	Defn            map[string]any `json:"defn"`
	Audio           string         `json:"audio"`
	SD              string         `json:"sd"`
	HD              string         `json:"hd"`
	SHD             string         `json:"shd"`
	FHD             string         `json:"fhd"`
	UHD             string         `json:"uhd"`
	Source          string         `json:"source"`
}

var cidPatterns = []*regexp.Regexp{
	regexp.MustCompile(`/cover/([^/]+)/[^/]+\.html`),
	regexp.MustCompile(`/cover/([^/]+)\.html`),
}

func main() {
	rawURL := flag.String("url", "", "Tencent video page URL")
	cid := flag.String("cid", "", "Cover ID")
	vidsCSV := flag.String("vids", "", "Comma-separated video IDs")
	jsonOutput := flag.Bool("json", false, "Print JSON output")
	flag.Parse()

	finalCID := strings.TrimSpace(*cid)
	if finalCID == "" && strings.TrimSpace(*rawURL) != "" {
		finalCID = extractCIDFromURL(*rawURL)
	}

	vids := splitCSV(*vidsCSV)
	if finalCID == "" && len(vids) == 0 {
		fmt.Fprintln(os.Stderr, "provide -url, -cid, or -vids")
		os.Exit(1)
	}

	var cover *coverInfo
	var err error
	if finalCID != "" {
		cover, err = fetchCoverInfo(finalCID)
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		if len(vids) == 0 {
			vids = cover.VideoIDs
		}
	}

	details, err := fetchVideoDetails(vids)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	payload := map[string]any{
		"cid":           finalCID,
		"cover_info":    cover,
		"video_details": details,
	}

	if *jsonOutput {
		enc := json.NewEncoder(os.Stdout)
		enc.SetEscapeHTML(false)
		enc.SetIndent("", "  ")
		_ = enc.Encode(payload)
		return
	}

	if cover != nil {
		fmt.Printf("CID: %s\n", cover.CID)
		fmt.Printf("标题: %s\n", cover.Title)
		fmt.Printf("类型: %s (%s)\n", cover.TypeName, cover.Type)
		fmt.Printf("VIDs: %s\n\n", strings.Join(cover.VideoIDs, ", "))
	}

	printTextTable(details)
}

func extractCIDFromURL(raw string) string {
	trimmed := strings.TrimSpace(raw)
	for _, pattern := range cidPatterns {
		match := pattern.FindStringSubmatch(trimmed)
		if len(match) == 2 {
			return match[1]
		}
	}
	return ""
}

func buildAPI1URL(cid string) string {
	values := url.Values{}
	values.Set("tid", "431")
	values.Set("idlist", cid)
	values.Set("appid", "10001005")
	values.Set("appkey", "0d1a9ddd94de871b")
	return api1URL + "?" + values.Encode()
}

func buildAPI2URL(vids []string) string {
	values := url.Values{}
	values.Set("otype", "xml")
	values.Set("tid", "535")
	values.Set("appid", "20001238")
	values.Set("appkey", "6c03bbe9658448a4")
	values.Set("union_platform", "3")
	values.Set("idlist", strings.Join(vids, ","))
	return api2URL + "?" + values.Encode()
}

func httpGet(raw string) (string, error) {
	client := &http.Client{Timeout: 10 * time.Second}
	req, err := http.NewRequest(http.MethodGet, raw, nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0")
	req.Header.Set("Accept", "*/*")

	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}
	if resp.StatusCode >= 400 {
		return "", fmt.Errorf("http %d: %s", resp.StatusCode, string(body))
	}
	return string(body), nil
}

func fetchCoverInfo(cid string) (*coverInfo, error) {
	xmlText, err := httpGet(buildAPI1URL(cid))
	if err != nil {
		return nil, err
	}
	if apiErr := firstTagValue(xmlText, "error"); apiErr != "" {
		return nil, fmt.Errorf("api1 error: %s", apiErr)
	}

	videoIDs := []string{}
	for _, raw := range allTagValues(xmlText, "video_ids") {
		videoIDs = append(videoIDs, splitCSV(raw)...)
	}

	return &coverInfo{
		CID:        cid,
		Title:      firstTagValue(xmlText, "title"),
		Type:       firstTagValue(xmlText, "type"),
		TypeName:   firstTagValue(xmlText, "type_name"),
		VideoIDs:   videoIDs,
		PayStatus:  firstTagValue(xmlText, "pay_status"),
		CoverPicHz: firstTagValue(xmlText, "new_pic_hz"),
		CoverPicVt: firstTagValue(xmlText, "new_pic_vt"),
	}, nil
}

func fetchVideoDetails(vids []string) ([]videoDetail, error) {
	if len(vids) == 0 {
		return nil, nil
	}

	xmlText, err := httpGet(buildAPI2URL(vids))
	if err != nil {
		return nil, err
	}
	if apiErr := firstTagValue(xmlText, "error"); apiErr != "" {
		return nil, fmt.Errorf("api2 error: %s", apiErr)
	}

	fieldPattern := regexp.MustCompile(`(?s)<field\b[^>]*>(.*?)</field>`)
	matches := fieldPattern.FindAllStringSubmatch(xmlText, -1)
	results := make([]videoDetail, 0, len(matches))

	for _, match := range matches {
		fieldXML := match[1]
		defnRaw := firstTagValue(fieldXML, "defn")
		defn := parseDefn(defnRaw)

		results = append(results, videoDetail{
			VID:             firstTagValue(fieldXML, "vid"),
			Title:           firstTagValue(fieldXML, "title"),
			DurationSeconds: firstTagValue(fieldXML, "duration"),
			Duration:        formatDuration(firstTagValue(fieldXML, "duration")),
			URL:             firstTagValue(fieldXML, "url"),
			CoverList:       firstTagValue(fieldXML, "cover_list"),
			Defn:            defn,
			Audio:           formatSize(defn["audio"]),
			SD:              formatSize(defn["sd"]),
			HD:              formatSize(defn["hd"]),
			SHD:             formatSize(defn["shd"]),
			FHD:             formatSize(defn["fhd"]),
			UHD:             formatSize(defn["uhd"]),
			Source:          formatSize(defn["source"]),
		})
	}

	return results, nil
}

func parseDefn(raw string) map[string]any {
	if strings.TrimSpace(raw) == "" {
		return map[string]any{}
	}
	var out map[string]any
	if err := json.Unmarshal([]byte(raw), &out); err != nil {
		return map[string]any{}
	}
	return out
}

func firstTagValue(text, tag string) string {
	values := allTagValues(text, tag)
	if len(values) == 0 {
		return ""
	}
	return values[0]
}

func allTagValues(text, tag string) []string {
	pattern := regexp.MustCompile(`(?s)<` + regexp.QuoteMeta(tag) + `>(.*?)</` + regexp.QuoteMeta(tag) + `>`)
	matches := pattern.FindAllStringSubmatch(text, -1)
	results := make([]string, 0, len(matches))
	for _, match := range matches {
		if len(match) > 1 {
			results = append(results, strings.TrimSpace(htmlUnescape(match[1])))
		}
	}
	return results
}

func htmlUnescape(text string) string {
	replacer := strings.NewReplacer(
		"&lt;", "<",
		"&gt;", ">",
		"&amp;", "&",
		"&quot;", "\"",
		"&#39;", "'",
	)
	return replacer.Replace(text)
}

func splitCSV(raw string) []string {
	parts := strings.Split(strings.TrimSpace(raw), ",")
	out := make([]string, 0, len(parts))
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part != "" {
			out = append(out, part)
		}
	}
	return out
}

func formatDuration(raw string) string {
	if strings.TrimSpace(raw) == "" {
		return "-"
	}
	var total int
	_, err := fmt.Sscanf(raw, "%d", &total)
	if err != nil {
		return raw
	}
	hours := total / 3600
	minutes := (total % 3600) / 60
	seconds := total % 60
	if hours > 0 {
		return fmt.Sprintf("%02d:%02d:%02d", hours, minutes, seconds)
	}
	return fmt.Sprintf("%02d:%02d", minutes, seconds)
}

func formatSize(value any) string {
	switch v := value.(type) {
	case nil:
		return "-"
	case float64:
		return humanSize(v)
	case int:
		return humanSize(float64(v))
	case string:
		if strings.TrimSpace(v) == "" {
			return "-"
		}
		var num float64
		_, err := fmt.Sscanf(v, "%f", &num)
		if err != nil {
			return v
		}
		return humanSize(num)
	default:
		return fmt.Sprintf("%v", value)
	}
}

func humanSize(size float64) string {
	units := []string{"B", "KB", "MB", "GB", "TB"}
	for _, unit := range units {
		if size < 1024 || unit == units[len(units)-1] {
			if unit == "B" {
				return fmt.Sprintf("%.0f %s", size, unit)
			}
			return fmt.Sprintf("%.1f %s", size, unit)
		}
		size /= 1024
	}
	return "-"
}

func printTextTable(items []videoDetail) {
	if len(items) == 0 {
		return
	}

	headers := []string{"title", "vid", "duration", "audio", "sd", "hd", "shd", "fhd", "uhd"}
	widths := map[string]int{}
	for _, header := range headers {
		widths[header] = len(header)
	}

	rows := make([]map[string]string, 0, len(items))
	for _, item := range items {
		row := map[string]string{
			"title":    item.Title,
			"vid":      item.VID,
			"duration": item.Duration,
			"audio":    item.Audio,
			"sd":       item.SD,
			"hd":       item.HD,
			"shd":      item.SHD,
			"fhd":      item.FHD,
			"uhd":      item.UHD,
		}
		for key, value := range row {
			if len(value) > widths[key] {
				widths[key] = len(value)
			}
		}
		rows = append(rows, row)
	}

	printRow(headers, widths)
	printSeparator(headers, widths)
	for _, row := range rows {
		values := make([]string, 0, len(headers))
		for _, header := range headers {
			values = append(values, row[header])
		}
		printAligned(values, headers, widths)
	}
}

func printRow(headers []string, widths map[string]int) {
	printAligned(headers, headers, widths)
}

func printSeparator(headers []string, widths map[string]int) {
	parts := make([]string, 0, len(headers))
	for _, header := range headers {
		parts = append(parts, strings.Repeat("-", widths[header]))
	}
	fmt.Println(strings.Join(parts, "-+-"))
}

func printAligned(values, headers []string, widths map[string]int) {
	parts := make([]string, 0, len(values))
	for idx, value := range values {
		header := headers[idx]
		parts = append(parts, fmt.Sprintf("%-*s", widths[header], value))
	}
	fmt.Println(strings.Join(parts, " | "))
}
