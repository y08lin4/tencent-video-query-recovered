package com.y08lin.tencentvideoquery;

import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.StringReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import javax.xml.parsers.DocumentBuilderFactory;
import org.json.JSONObject;
import org.w3c.dom.Document;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

public class MainActivity extends AppCompatActivity {
    private static final Pattern[] CID_PATTERNS = new Pattern[] {
        Pattern.compile("/cover/([^/]+)/[^/]+\\.html"),
        Pattern.compile("/cover/([^/]+)\\.html")
    };

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private EditText inputUrl;
    private Button buttonQuery;
    private TextView resultView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        inputUrl = findViewById(R.id.input_url);
        buttonQuery = findViewById(R.id.button_query);
        resultView = findViewById(R.id.result_view);

        buttonQuery.setOnClickListener(v -> runQuery());
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        executor.shutdownNow();
    }

    private void runQuery() {
        String raw = inputUrl.getText().toString().trim();
        if (raw.isEmpty()) {
            resultView.setText("请输入腾讯视频地址");
            return;
        }

        String cid = extractCid(raw);
        if (cid == null || cid.isEmpty()) {
            resultView.setText("未能从输入中提取 CID");
            return;
        }

        buttonQuery.setEnabled(false);
        resultView.setText("查询中...");

        executor.execute(() -> {
            try {
                CoverInfo coverInfo = fetchCoverInfo(cid);
                List<VideoDetail> details = fetchVideoDetails(coverInfo.videoIds);
                String text = buildResultText(coverInfo, details);
                runOnUiThread(() -> {
                    resultView.setText(text);
                    buttonQuery.setEnabled(true);
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    resultView.setText("查询失败:\n" + e.getMessage());
                    buttonQuery.setEnabled(true);
                });
            }
        });
    }

    private String extractCid(String raw) {
        for (Pattern pattern : CID_PATTERNS) {
            Matcher matcher = pattern.matcher(raw);
            if (matcher.find()) {
                return matcher.group(1);
            }
        }
        return null;
    }

    private CoverInfo fetchCoverInfo(String cid) throws Exception {
        String url = "https://data.video.qq.com/fcgi-bin/data"
            + "?tid=431"
            + "&idlist=" + URLEncoder.encode(cid, StandardCharsets.UTF_8)
            + "&appid=10001005"
            + "&appkey=0d1a9ddd94de871b";

        Document document = parseXml(httpGet(url));
        String apiError = firstTagText(document, "errormsg");
        String errorNo = firstTagText(document, "errorno");
        if (!apiError.isEmpty() || (!errorNo.isEmpty() && !"0".equals(errorNo))) {
            throw new IllegalStateException(apiError.isEmpty() ? "API1 errorno=" + errorNo : apiError);
        }

        List<String> videoIds = new ArrayList<>();
        NodeList videoNodes = document.getElementsByTagName("video_ids");
        for (int i = 0; i < videoNodes.getLength(); i++) {
            String text = videoNodes.item(i).getTextContent().trim();
            if (!text.isEmpty()) {
                for (String part : text.split(",")) {
                    String trimmed = part.trim();
                    if (!trimmed.isEmpty()) {
                        videoIds.add(trimmed);
                    }
                }
            }
        }

        CoverInfo coverInfo = new CoverInfo();
        coverInfo.cid = cid;
        coverInfo.title = firstTagText(document, "title");
        coverInfo.type = firstTagText(document, "type");
        coverInfo.typeName = firstTagText(document, "type_name");
        coverInfo.videoIds = videoIds;
        coverInfo.payStatus = firstTagText(document, "pay_status");
        return coverInfo;
    }

    private List<VideoDetail> fetchVideoDetails(List<String> vids) throws Exception {
        List<VideoDetail> details = new ArrayList<>();
        if (vids == null || vids.isEmpty()) {
            return details;
        }

        String url = "https://union.video.qq.com/fcgi-bin/data"
            + "?otype=xml"
            + "&tid=535"
            + "&appid=20001238"
            + "&appkey=6c03bbe9658448a4"
            + "&union_platform=3"
            + "&idlist=" + URLEncoder.encode(String.join(",", vids), StandardCharsets.UTF_8);

        Document document = parseXml(httpGet(url));
        String apiError = firstTagText(document, "errormsg");
        String errorNo = firstTagText(document, "errorno");
        if (!apiError.isEmpty() || (!errorNo.isEmpty() && !"0".equals(errorNo))) {
            throw new IllegalStateException(apiError.isEmpty() ? "API2 errorno=" + errorNo : apiError);
        }

        NodeList resultNodes = document.getElementsByTagName("results");
        for (int i = 0; i < resultNodes.getLength(); i++) {
            org.w3c.dom.Element resultElement = (org.w3c.dom.Element) resultNodes.item(i);
            NodeList fieldsNodes = resultElement.getElementsByTagName("fields");
            if (fieldsNodes.getLength() == 0) {
                continue;
            }

            org.w3c.dom.Element fieldsElement = (org.w3c.dom.Element) fieldsNodes.item(0);
            VideoDetail detail = new VideoDetail();
            detail.vid = firstChildTagText(fieldsElement, "vid");
            if (detail.vid.isEmpty()) {
                detail.vid = firstChildTagText(resultElement, "id");
            }
            detail.title = firstChildTagText(fieldsElement, "title");
            detail.durationSeconds = firstChildTagText(fieldsElement, "duration");
            detail.duration = formatDuration(detail.durationSeconds);
            detail.url = firstChildTagText(fieldsElement, "url");

            String defnRaw = firstChildTagText(fieldsElement, "defn");
            JSONObject defn = defnRaw.isEmpty() ? new JSONObject() : new JSONObject(defnRaw);
            detail.audio = formatSize(defn.optDouble("audio", -1));
            detail.sd = formatSize(defn.optDouble("sd", -1));
            detail.hd = formatSize(defn.optDouble("hd", -1));
            detail.shd = formatSize(defn.optDouble("shd", -1));
            detail.fhd = formatSize(defn.optDouble("fhd", -1));
            detail.uhd = formatSize(defn.optDouble("uhd", -1));
            detail.source = formatSize(defn.optDouble("source", -1));
            details.add(detail);
        }

        return details;
    }

    private String buildResultText(CoverInfo coverInfo, List<VideoDetail> details) {
        StringBuilder sb = new StringBuilder();
        sb.append("CID: ").append(coverInfo.cid).append('\n');
        sb.append("标题: ").append(coverInfo.title).append('\n');
        sb.append("类型: ").append(coverInfo.typeName).append(" (").append(coverInfo.type).append(")").append('\n');
        sb.append("VIDs: ").append(String.join(", ", coverInfo.videoIds)).append("\n\n");

        for (VideoDetail detail : details) {
            sb.append(detail.title).append('\n');
            sb.append("VID: ").append(detail.vid).append('\n');
            sb.append("时长: ").append(detail.duration).append('\n');
            sb.append("音频: ").append(detail.audio).append('\n');
            sb.append("标清: ").append(detail.sd).append('\n');
            sb.append("高清: ").append(detail.hd).append('\n');
            sb.append("超清: ").append(detail.shd).append('\n');
            sb.append("蓝光: ").append(detail.fhd).append('\n');
            sb.append("4K: ").append(detail.uhd).append("\n\n");
        }

        return sb.toString().trim();
    }

    private String httpGet(String rawUrl) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(rawUrl).openConnection();
        connection.setRequestMethod("GET");
        connection.setConnectTimeout(10000);
        connection.setReadTimeout(10000);
        connection.setRequestProperty("User-Agent", "Mozilla/5.0");
        connection.setRequestProperty("Accept", "*/*");

        try (BufferedReader reader = new BufferedReader(
            new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8))) {
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
            return sb.toString();
        }
    }

    private Document parseXml(String xml) throws Exception {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setNamespaceAware(false);
        return factory.newDocumentBuilder().parse(new InputSource(new StringReader(xml)));
    }

    private String firstTagText(Document document, String tagName) {
        NodeList nodes = document.getElementsByTagName(tagName);
        if (nodes.getLength() == 0) {
            return "";
        }
        return nodes.item(0).getTextContent().trim();
    }

    private String firstChildTagText(org.w3c.dom.Element parent, String childTag) {
        NodeList children = parent.getElementsByTagName(childTag);
        if (children.getLength() == 0) {
            return "";
        }
        return children.item(0).getTextContent().trim();
    }

    private String formatDuration(String raw) {
        if (raw == null || raw.isEmpty()) {
            return "-";
        }
        try {
            int total = Integer.parseInt(raw);
            int hours = total / 3600;
            int minutes = (total % 3600) / 60;
            int seconds = total % 60;
            if (hours > 0) {
                return String.format(Locale.US, "%02d:%02d:%02d", hours, minutes, seconds);
            }
            return String.format(Locale.US, "%02d:%02d", minutes, seconds);
        } catch (NumberFormatException e) {
            return raw;
        }
    }

    private String formatSize(double value) {
        if (value < 0) {
            return "-";
        }
        String[] units = {"B", "KB", "MB", "GB", "TB"};
        int index = 0;
        while (value >= 1024 && index < units.length - 1) {
            value /= 1024;
            index++;
        }
        if (index == 0) {
            return String.format(Locale.US, "%.0f %s", value, units[index]);
        }
        return String.format(Locale.US, "%.1f %s", value, units[index]);
    }

    private static class CoverInfo {
        String cid;
        String title;
        String type;
        String typeName;
        List<String> videoIds;
        String payStatus;
    }

    private static class VideoDetail {
        String vid;
        String title;
        String durationSeconds;
        String duration;
        String url;
        String audio;
        String sd;
        String hd;
        String shd;
        String fhd;
        String uhd;
        String source;
    }
}
