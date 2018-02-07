package com.ufrpe.lenfila;

import android.support.v7.app.AppCompatActivity;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.SeekBar;
import android.widget.TextView;
import android.widget.Toast;

import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.Response;
import com.android.volley.VolleyError;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.Volley;

import org.json.JSONException;
import org.json.JSONObject;

import java.text.Format;
import java.text.SimpleDateFormat;
import java.util.Date;

public class MainActivity extends AppCompatActivity {
    Button button;
    TextView textView;
    String serverUrl = "http://172.16.204.174:5000/api/tamanho";
    ProgressBar progressBar;


    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        button = (Button)findViewById(R.id.bn);
        textView = (TextView)findViewById(R.id.txt);
        progressBar = (ProgressBar) findViewById(R.id.progressBar2);

        callByJsonObject();

        button.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                callByJsonObject();

            }
        });
    }
    public int checkCheckpoint(int checkpoint){

        if(checkpoint == 0){
            return 0;
        }else  if(checkpoint == 1){
            return 50;
        }else{
            return 100;
        }

    }

    public void callByJsonObject(){
        final RequestQueue requestQueue = Volley.newRequestQueue(MainActivity.this);
        JsonObjectRequest jsonObjectRequest = new JsonObjectRequest(Request.Method.GET, serverUrl,
                new Response.Listener<JSONObject>() {
                    @Override
                    public void onResponse(JSONObject response) {
                        String resposta = response.toString();

                        try {
                            JSONObject json = response.getJSONObject("tamanhoAtual");
                            long timestamp = json.getLong("timestamp");
                            Date d = new Date(timestamp *1000L);
                            Format formatter = new SimpleDateFormat("dd-MM-yyyy HH:mm:ss");
                            String dateformat = formatter.format(d);


                            textView.setText("Ultima atualizacao: " + dateformat);
                            int checkponit = json.getInt("checkpointAtingido");
                            int status = checkCheckpoint(checkponit);
                            progressBar.setProgress(status);

                        } catch (JSONException e) {
                            Toast.makeText(MainActivity.this, e.toString(), Toast.LENGTH_SHORT).show();
                            e.printStackTrace();
                        }



                        Toast.makeText(MainActivity.this, resposta, Toast.LENGTH_LONG).show();
                        requestQueue.stop();
                    }
                }, new Response.ErrorListener() {
            @Override
            public void onErrorResponse(VolleyError error) {
                String resposta = error.toString();
                Toast.makeText(MainActivity.this, resposta, Toast.LENGTH_LONG).show();
                error.printStackTrace();
                requestQueue.stop();
            }
        });
        requestQueue.add(jsonObjectRequest);

    }
}
