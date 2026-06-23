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
	"sort"
	"strings"
	"time"
)

const (
	api1URL = "https://data.video.qq.com/fcgi-bin/data"
	api2URL = "https://union.video.qq.com/fcgi-bin/data"
)

type api1Options struct {
	Tid    string
	AppID  string
	AppKey string
}

type api2Options struct {
	OType         string
	Tid           string
	AppID         string
	AppKey        string
	UnionPlatform string
	Callback      string
	CallbackSet   bool
	BatchSize     int
}

type requestOptions struct {
	Headers map[string]string
	Timeout time.Duration
}

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
	ResultID        string         `json:"result_id"`
	RetCode         string         `json:"retcode"`
	VID             string         `json:"vid"`
	Title           string         `json:"title"`
	DurationSeconds string         `json:"duration_seconds"`
	Duration        string         `json:"duration"`
	URL             string         `json:"url"`
	CoverList       []string       `json:"cover_list"`
	CategoryMap     []string       `json:"category_map"`
	VWH             []string       `json:"vwh"`
	Defn            map[string]any `json:"defn"`
	State           string         `json:"state"`
	UploadSrc       string         `json:"upload_src"`
	CreateTime      string         `json:"create_time"`
	ModifyTime      string         `json:"modify_time"`
	Audio           string         `json:"audio"`
	SD              string         `json:"sd"`
	HD              string         `json:"hd"`
	SHD             string         `json:"shd"`
	FHD             string         `json:"fhd"`
	UHD             string         `json:"uhd"`
	Source          string         `json:"source"`
	EmptyShell      bool           `json:"empty_shell"`
}

type api2BatchDiagnostics struct {
	ResultsCount         int    `json:"results_count"`
	EmptyShellCount      int    `json:"empty_shell_count"`
	NonemptyResultCount  int    `json:"nonempty_result_count"`
	AllResultsEmptyShell bool   `json:"all_results_empty_shell"`
	CallerRule           string `json:"caller_rule"`
}

type api1BatchDiagnostics struct {
	RequestedCIDs           []string `json:"requested_cids"`
	RequestedCIDCount       int      `json:"requested_cid_count"`
	ReturnedCoverCount      int      `json:"returned_cover_count"`
	ReturnedCIDs            []string `json:"returned_cids"`
	AggregatedVideoIDsCount int      `json:"aggregated_video_ids_count"`
	AggregatedVideoIDsHead  []string `json:"aggregated_video_ids_head"`
}

var cidPatterns = []*regexp.Regexp{
	regexp.MustCompile(`/cover/([^/]+)/[^/]+\.html`),
	regexp.MustCompile(`/cover/([^/]+)\.html`),
}

func main() {
	rawURL := flag.String("url", "", "Tencent video page URL")
	cid := flag.String("cid", "", "Cover ID")
	vidsCSV := flag.String("vids", "", "Comma-separated video IDs")
	api1Tid := flag.String("api1-tid", "431", "API1 tid")
	api1AppID := flag.String("api1-appid", "10001005", "API1 appid")
	api1AppKey := flag.String("api1-appkey", "0d1a9ddd94de871b", "API1 appkey")
	api2OType := flag.String("api2-otype", "xml", "API2 wrapper mode: xml or json")
	api2Tid := flag.String("api2-tid", "535", "API2 tid")
	api2AppID := flag.String("api2-appid", "20001238", "API2 appid")
	api2AppKey := flag.String("api2-appkey", "6c03bbe9658448a4", "API2 appkey")
	api2UnionPlatform := flag.String("api2-union-platform", "3", "API2 union_platform")
	api2Callback := flag.String("api2-callback", "", "API2 JSONP callback override; only applies when -api2-otype json")
	api2BatchSize := flag.Int("api2-batch-size", 10, "API2 batch size")
	envJSON := flag.String("env-json", "", "Path to a replay environment JSON file")
	envName := flag.String("env-name", "", "Environment name inside -env-json, such as pc_web_real_cookie_replay")
	timeoutSeconds := flag.Int("timeout", 10, "HTTP timeout in seconds")
	jsonOutput := flag.Bool("json", false, "Print JSON output")
	flag.Parse()

	if *api2BatchSize <= 0 || *api2BatchSize > 32 {
		fmt.Fprintln(os.Stderr, "-api2-batch-size must be between 1 and 32")
		os.Exit(1)
	}
	if *timeoutSeconds <= 0 {
		fmt.Fprintln(os.Stderr, "-timeout must be > 0")
		os.Exit(1)
	}

	api1Opts := api1Options{
		Tid:    strings.TrimSpace(*api1Tid),
		AppID:  strings.TrimSpace(*api1AppID),
		AppKey: strings.TrimSpace(*api1AppKey),
	}
	api2Opts := api2Options{
		OType:         strings.TrimSpace(*api2OType),
		Tid:           strings.TrimSpace(*api2Tid),
		AppID:         strings.TrimSpace(*api2AppID),
		AppKey:        strings.TrimSpace(*api2AppKey),
		UnionPlatform: strings.TrimSpace(*api2UnionPlatform),
		Callback:      *api2Callback,
		CallbackSet:   hasFlag("api2-callback"),
		BatchSize:     *api2BatchSize,
	}
	if api2Opts.OType != "xml" && api2Opts.OType != "json" {
		fmt.Fprintln(os.Stderr, "-api2-otype must be xml or json")
		os.Exit(1)
	}
	requestOpts, resolvedEnvName, err := loadRequestOptions(*envJSON, *envName, time.Duration(*timeoutSeconds)*time.Second)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	finalCID := strings.TrimSpace(*cid)
	if finalCID == "" && strings.TrimSpace(*rawURL) != "" {
		finalCID = extractCIDFromURL(*rawURL)
	}
	requestedCIDs := splitCSV(finalCID)

	vids := splitCSV(*vidsCSV)
	if len(requestedCIDs) == 0 && len(vids) == 0 {
		fmt.Fprintln(os.Stderr, "provide -url, -cid, or -vids")
		os.Exit(1)
	}

	var cover *coverInfo
	var covers []coverInfo
	if len(requestedCIDs) > 0 {
		covers, err = fetchCoverInfos(requestedCIDs, api1Opts, requestOpts)
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		if len(covers) > 0 {
			cover = &covers[0]
		}
		if len(vids) == 0 {
			for _, item := range covers {
				vids = append(vids, item.VideoIDs...)
			}
		}
	}

	details, err := fetchVideoDetails(vids, api2Opts, requestOpts)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	payload := map[string]any{
		"cid":         strings.Join(requestedCIDs, ","),
		"cids":        requestedCIDs,
		"api1_params": api1Opts,
		"api2_params": api2Opts,
		"request_environment": map[string]any{
			"env_json":        strings.TrimSpace(*envJSON),
			"env_name":        resolvedEnvName,
			"timeout_seconds": *timeoutSeconds,
			"header_keys":     sortedHeaderKeys(requestOpts.Headers),
		},
		"cover_info":             cover,
		"cover_infos":            covers,
		"api1_batch_diagnostics": summarizeAPI1Batch(requestedCIDs, covers),
		"api2_batch_diagnostics": summarizeAPI2Batch(details),
		"video_details":          details,
	}

	if *jsonOutput {
		enc := json.NewEncoder(os.Stdout)
		enc.SetEscapeHTML(false)
		enc.SetIndent("", "  ")
		_ = enc.Encode(payload)
		return
	}

	if len(covers) == 1 && cover != nil {
		fmt.Printf("CID: %s\n", cover.CID)
		fmt.Printf("标题: %s\n", cover.Title)
		fmt.Printf("类型: %s (%s)\n", cover.TypeName, cover.Type)
		fmt.Printf("VIDs: %s\n\n", strings.Join(cover.VideoIDs, ", "))
	} else if len(covers) > 1 {
		diagnostics := summarizeAPI1Batch(requestedCIDs, covers)
		fmt.Printf("CIDs: %s\n", strings.Join(requestedCIDs, ", "))
		fmt.Printf("返回 cover 数: %d\n", diagnostics.ReturnedCoverCount)
		fmt.Printf("聚合 VIDs: %d\n\n", diagnostics.AggregatedVideoIDsCount)
		for idx, item := range covers {
			fmt.Printf("[%d] CID: %s\n", idx+1, item.CID)
			fmt.Printf("    标题: %s\n", item.Title)
			fmt.Printf("    类型: %s (%s)\n", item.TypeName, item.Type)
			fmt.Printf("    VIDs: %s\n", strings.Join(item.VideoIDs, ", "))
		}
		fmt.Println()
	}

	printTextTable(details)
	diagnostics := summarizeAPI2Batch(details)
	if diagnostics.AllResultsEmptyShell {
		fmt.Printf("\n注意: 当前 API2 批量结果为 top-level success + 全部 empty-shell，调用方应按全坏/全空批量处理。\n")
	}
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

func buildAPI1URL(cid string, opts api1Options) string {
	values := url.Values{}
	values.Set("tid", opts.Tid)
	values.Set("idlist", cid)
	values.Set("appid", opts.AppID)
	values.Set("appkey", opts.AppKey)
	return api1URL + "?" + values.Encode()
}

func buildAPI2URL(vids []string, opts api2Options) string {
	values := url.Values{}
	values.Set("otype", opts.OType)
	values.Set("tid", opts.Tid)
	values.Set("appid", opts.AppID)
	values.Set("appkey", opts.AppKey)
	values.Set("union_platform", opts.UnionPlatform)
	if opts.CallbackSet {
		values.Set("callback", opts.Callback)
	}
	values.Set("idlist", strings.Join(vids, ","))
	return api2URL + "?" + values.Encode()
}

func httpGet(raw string, requestOpts requestOptions) (string, error) {
	timeout := requestOpts.Timeout
	if timeout <= 0 {
		timeout = 10 * time.Second
	}
	client := &http.Client{Timeout: timeout}
	req, err := http.NewRequest(http.MethodGet, raw, nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0")
	req.Header.Set("Accept", "*/*")
	for key, value := range requestOpts.Headers {
		if strings.TrimSpace(key) != "" && strings.TrimSpace(value) != "" {
			req.Header.Set(key, value)
		}
	}

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

func fetchCoverInfos(cids []string, opts api1Options, requestOpts requestOptions) ([]coverInfo, error) {
	xmlText, err := httpGet(buildAPI1URL(strings.Join(cids, ","), opts), requestOpts)
	if err != nil {
		return nil, err
	}
	apiErr := firstTagValue(xmlText, "errormsg")
	errorNo := firstTagValue(xmlText, "errorno")
	if apiErr != "" || (errorNo != "" && errorNo != "0") {
		if apiErr == "" {
			apiErr = "api1 errorno=" + errorNo
		}
		return nil, fmt.Errorf(apiErr)
	}

	resultPattern := regexp.MustCompile(`(?s)<results>(.*?)</results>`)
	matches := resultPattern.FindAllStringSubmatch(xmlText, -1)
	results := make([]coverInfo, 0, len(matches))
	for _, match := range matches {
		if len(match) < 2 {
			continue
		}
		fieldsXML := firstTagValue(match[1], "fields")
		if strings.TrimSpace(fieldsXML) == "" {
			continue
		}
		videoIDs := []string{}
		for _, raw := range allTagValues(fieldsXML, "video_ids") {
			videoIDs = append(videoIDs, splitCSV(raw)...)
		}
		results = append(results, coverInfo{
			CID:        firstNonEmpty(firstTagValue(fieldsXML, "cover_id"), firstTagValue(match[1], "id")),
			Title:      firstTagValue(fieldsXML, "title"),
			Type:       firstTagValue(fieldsXML, "type"),
			TypeName:   firstTagValue(fieldsXML, "type_name"),
			VideoIDs:   videoIDs,
			PayStatus:  firstTagValue(fieldsXML, "pay_status"),
			CoverPicHz: firstTagValue(fieldsXML, "new_pic_hz"),
			CoverPicVt: firstTagValue(fieldsXML, "new_pic_vt"),
		})
	}

	return results, nil
}

func fetchVideoDetails(vids []string, opts api2Options, requestOpts requestOptions) ([]videoDetail, error) {
	if len(vids) == 0 {
		return nil, nil
	}

	if opts.BatchSize <= 0 {
		opts.BatchSize = 10
	}

	results := []videoDetail{}
	for start := 0; start < len(vids); start += opts.BatchSize {
		end := start + opts.BatchSize
		if end > len(vids) {
			end = len(vids)
		}
		batchResults, err := fetchVideoDetailBatch(vids[start:end], opts, requestOpts)
		if err != nil {
			return nil, err
		}
		results = append(results, batchResults...)
	}
	return results, nil
}

func fetchVideoDetailBatch(vids []string, opts api2Options, requestOpts requestOptions) ([]videoDetail, error) {
	body, err := httpGet(buildAPI2URL(vids, opts), requestOpts)
	if err != nil {
		return nil, err
	}
	if opts.OType == "json" {
		return parseAPI2JSONPBody(body)
	}
	return parseAPI2XMLBody(body)
}

func parseAPI2XMLBody(xmlText string) ([]videoDetail, error) {
	apiErr := firstTagValue(xmlText, "errormsg")
	errorNo := firstTagValue(xmlText, "errorno")
	if apiErr != "" || (errorNo != "" && errorNo != "0") {
		if apiErr == "" {
			apiErr = "api2 errorno=" + errorNo
		}
		return nil, fmt.Errorf(apiErr)
	}

	resultPattern := regexp.MustCompile(`(?s)<results>(.*?)</results>`)
	matches := resultPattern.FindAllStringSubmatch(xmlText, -1)
	results := make([]videoDetail, 0, len(matches))

	for _, match := range matches {
		resultXML := match[1]
		fieldsXML := firstTagValue(resultXML, "fields")
		if strings.TrimSpace(fieldsXML) == "" {
			continue
		}
		defnRaw := firstTagValue(fieldsXML, "defn")
		defn := parseDefn(defnRaw)

		results = append(results, videoDetail{
			ResultID:        firstTagValue(resultXML, "id"),
			RetCode:         firstTagValue(resultXML, "retcode"),
			VID:             firstTagValue(fieldsXML, "vid"),
			Title:           firstTagValue(fieldsXML, "title"),
			DurationSeconds: firstTagValue(fieldsXML, "duration"),
			Duration:        formatDuration(firstTagValue(fieldsXML, "duration")),
			URL:             firstTagValue(fieldsXML, "url"),
			CoverList:       allTagValues(fieldsXML, "cover_list"),
			CategoryMap:     allTagValues(fieldsXML, "category_map"),
			VWH:             allTagValues(fieldsXML, "vWH"),
			Defn:            defn,
			State:           firstTagValue(fieldsXML, "state"),
			UploadSrc:       firstTagValue(fieldsXML, "upload_src"),
			CreateTime:      firstTagValue(fieldsXML, "create_time"),
			ModifyTime:      firstTagValue(fieldsXML, "modify_time"),
			Audio:           formatSize(defn["audio"]),
			SD:              formatSize(defn["sd"]),
			HD:              formatSize(defn["hd"]),
			SHD:             formatSize(defn["shd"]),
			FHD:             formatSize(defn["fhd"]),
			UHD:             formatSize(defn["uhd"]),
			Source:          formatSize(defn["source"]),
		})
		results[len(results)-1].EmptyShell = isVideoDetailEmptyShell(results[len(results)-1])
	}

	return results, nil
}

type api2JSONPResult struct {
	ID      any            `json:"id"`
	RetCode any            `json:"retcode"`
	Fields  map[string]any `json:"fields"`
}

type api2JSONPEnvelope struct {
	ErrorNo  any               `json:"errorno"`
	ErrorMsg string            `json:"errormsg"`
	Results  []api2JSONPResult `json:"results"`
}

func parseAPI2JSONPBody(body string) ([]videoDetail, error) {
	const prefix = "QZOutputJson="
	payload := ""
	if strings.HasPrefix(body, prefix) {
		payload = strings.TrimSpace(strings.TrimSuffix(strings.TrimPrefix(body, prefix), ";"))
	} else {
		openParen := strings.Index(body, "(")
		closeParen := strings.LastIndex(body, ")")
		if openParen <= 0 || closeParen <= openParen {
			return nil, fmt.Errorf("api2 JSONP wrapper missing or unparseable")
		}
		payload = strings.TrimSpace(body[openParen+1 : closeParen])
	}

	var envelope api2JSONPEnvelope
	if err := json.Unmarshal([]byte(payload), &envelope); err != nil {
		return nil, err
	}
	errorNo := strings.TrimSpace(toString(envelope.ErrorNo))
	apiErr := strings.TrimSpace(envelope.ErrorMsg)
	if apiErr != "" || (errorNo != "" && errorNo != "0") {
		if apiErr == "" {
			apiErr = "api2 errorno=" + errorNo
		}
		return nil, fmt.Errorf(apiErr)
	}

	results := make([]videoDetail, 0, len(envelope.Results))
	for _, result := range envelope.Results {
		if result.Fields == nil {
			continue
		}
		defn := parseDefnAny(result.Fields["defn"])
		results = append(results, videoDetail{
			ResultID:        toString(result.ID),
			RetCode:         toString(result.RetCode),
			VID:             toString(result.Fields["vid"]),
			Title:           toString(result.Fields["title"]),
			DurationSeconds: toString(result.Fields["duration"]),
			Duration:        formatDuration(toString(result.Fields["duration"])),
			URL:             toString(result.Fields["url"]),
			CoverList:       stringSliceFromAny(result.Fields["cover_list"]),
			CategoryMap:     stringSliceFromAny(result.Fields["category_map"]),
			VWH:             stringSliceFromAny(result.Fields["vWH"]),
			Defn:            defn,
			State:           toString(result.Fields["state"]),
			UploadSrc:       toString(result.Fields["upload_src"]),
			CreateTime:      toString(result.Fields["create_time"]),
			ModifyTime:      toString(result.Fields["modify_time"]),
			Audio:           formatSize(defn["audio"]),
			SD:              formatSize(defn["sd"]),
			HD:              formatSize(defn["hd"]),
			SHD:             formatSize(defn["shd"]),
			FHD:             formatSize(defn["fhd"]),
			UHD:             formatSize(defn["uhd"]),
			Source:          formatSize(defn["source"]),
		})
		results[len(results)-1].EmptyShell = isVideoDetailEmptyShell(results[len(results)-1])
	}
	return results, nil
}

func loadRequestOptions(envJSONPath, envName string, timeout time.Duration) (requestOptions, string, error) {
	opts := requestOptions{
		Headers: map[string]string{},
		Timeout: timeout,
	}
	if strings.TrimSpace(envJSONPath) == "" {
		return opts, "", nil
	}

	data, err := os.ReadFile(envJSONPath)
	if err != nil {
		return opts, "", err
	}

	var payload map[string]any
	if err := json.Unmarshal(data, &payload); err != nil {
		return opts, "", err
	}

	selectedName := strings.TrimSpace(envName)
	var selected any
	if selectedName != "" {
		var ok bool
		selected, ok = payload[selectedName]
		if !ok {
			return opts, "", fmt.Errorf("env name %q not found in env json; available: %s", selectedName, strings.Join(sortedMapKeys(payload), ", "))
		}
	} else if headerMap, ok := directStringMap(payload); ok {
		opts.Headers = headerMap
		return opts, "", nil
	} else if len(payload) == 1 {
		for key, value := range payload {
			selectedName = key
			selected = value
		}
	} else {
		return opts, "", fmt.Errorf("env json contains multiple named environments; pass -env-name from: %s", strings.Join(sortedMapKeys(payload), ", "))
	}

	headerMap, err := stringMapFromAny(selected)
	if err != nil {
		return opts, "", err
	}
	opts.Headers = headerMap
	return opts, selectedName, nil
}

func directStringMap(payload map[string]any) (map[string]string, bool) {
	out := map[string]string{}
	for key, value := range payload {
		valueText, ok := value.(string)
		if !ok {
			return nil, false
		}
		key = strings.TrimSpace(key)
		valueText = strings.TrimSpace(valueText)
		if key != "" && valueText != "" {
			out[key] = valueText
		}
	}
	return out, true
}

func stringMapFromAny(raw any) (map[string]string, error) {
	obj, ok := raw.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("selected env payload must be an object of request headers")
	}
	out := map[string]string{}
	for key, value := range obj {
		key = strings.TrimSpace(key)
		valueText := strings.TrimSpace(toString(value))
		if key != "" && valueText != "" {
			out[key] = valueText
		}
	}
	return out, nil
}

func sortedMapKeys(payload map[string]any) []string {
	keys := make([]string, 0, len(payload))
	for key := range payload {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func sortedHeaderKeys(headers map[string]string) []string {
	keys := make([]string, 0, len(headers))
	for key := range headers {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func isVideoDetailEmptyShell(detail videoDetail) bool {
	return strings.TrimSpace(detail.VID) == "" &&
		strings.TrimSpace(detail.Title) == "" &&
		strings.TrimSpace(detail.DurationSeconds) == "" &&
		strings.TrimSpace(detail.State) == "" &&
		strings.TrimSpace(detail.UploadSrc) == "" &&
		strings.TrimSpace(detail.CreateTime) == "" &&
		strings.TrimSpace(detail.ModifyTime) == "" &&
		len(detail.CoverList) == 0 &&
		len(detail.CategoryMap) == 0 &&
		len(detail.VWH) == 0 &&
		len(detail.Defn) == 0
}

func summarizeAPI2Batch(details []videoDetail) api2BatchDiagnostics {
	emptyShellCount := 0
	for _, detail := range details {
		if detail.EmptyShell {
			emptyShellCount++
		}
	}
	return api2BatchDiagnostics{
		ResultsCount:         len(details),
		EmptyShellCount:      emptyShellCount,
		NonemptyResultCount:  len(details) - emptyShellCount,
		AllResultsEmptyShell: len(details) > 0 && emptyShellCount == len(details),
		CallerRule:           "Treat top-level API2 success plus all results empty_shell=true as an all-invalid/empty-shell batch; do not rely on top-level errorno or per-result retcode alone.",
	}
}

func summarizeAPI1Batch(requestedCIDs []string, covers []coverInfo) api1BatchDiagnostics {
	returnedCIDs := make([]string, 0, len(covers))
	aggregatedVideoIDs := []string{}
	for _, item := range covers {
		if strings.TrimSpace(item.CID) != "" {
			returnedCIDs = append(returnedCIDs, item.CID)
		}
		aggregatedVideoIDs = append(aggregatedVideoIDs, item.VideoIDs...)
	}
	head := aggregatedVideoIDs
	if len(head) > 10 {
		head = head[:10]
	}
	return api1BatchDiagnostics{
		RequestedCIDs:           requestedCIDs,
		RequestedCIDCount:       len(requestedCIDs),
		ReturnedCoverCount:      len(covers),
		ReturnedCIDs:            returnedCIDs,
		AggregatedVideoIDsCount: len(aggregatedVideoIDs),
		AggregatedVideoIDsHead:  head,
	}
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
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

func parseDefnAny(raw any) map[string]any {
	switch v := raw.(type) {
	case nil:
		return map[string]any{}
	case map[string]any:
		return v
	case string:
		return parseDefn(v)
	default:
		return map[string]any{}
	}
}

func toString(value any) string {
	switch v := value.(type) {
	case nil:
		return ""
	case string:
		return strings.TrimSpace(v)
	default:
		return strings.TrimSpace(fmt.Sprintf("%v", value))
	}
}

func stringSliceFromAny(value any) []string {
	switch v := value.(type) {
	case nil:
		return nil
	case string:
		if strings.TrimSpace(v) == "" {
			return nil
		}
		return []string{strings.TrimSpace(v)}
	case []any:
		out := []string{}
		for _, item := range v {
			text := toString(item)
			if text != "" {
				out = append(out, text)
			}
		}
		return out
	default:
		text := toString(v)
		if text == "" {
			return nil
		}
		return []string{text}
	}
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
		"&#34;", "\"",
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

func hasFlag(name string) bool {
	for _, arg := range os.Args[1:] {
		if arg == "-"+name || arg == "--"+name {
			return true
		}
		if strings.HasPrefix(arg, "-"+name+"=") || strings.HasPrefix(arg, "--"+name+"=") {
			return true
		}
	}
	return false
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
