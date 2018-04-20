% Template MATLAB code for visualizing correlated data using the
% THINGSPEAKSCATTER function.

% Prior to running this MATLAB code template, assign the channel ID to read
% data from to the 'readChannelID' variable. Also, assign the field IDs
% within the channel that you want to read data from to 'fieldID1', and
% 'fieldID2'. 

% TODO - Replace the [] with channel ID to read data from:
readChannelID = [PUT HERE CHANNEL];

writeChannelID = [PUT HERE CHANNEL];
% TODO - Replace the [] with the Field ID to read data from:
fieldID1 = [1];
% TODO - Replace the [] with the Field ID to read data from:
fieldID2 = [2];

fieldID3 = [3];

% Channel Read API Key 
% If your channel is private, then enter the read API
% Key between the '' below: 
readAPIKey = 'PUT HERE KEY';
writeAPIKey = 'PUT HERE KEY';

%% Read Data %%
NumPoints = 600;

% Read first data variable
[CO2,time] = thingSpeakRead(readChannelID, 'Field', fieldID1, 'NumPoints', NumPoints, 'ReadKey', readAPIKey);

% Read second data variable
Temp = thingSpeakRead(readChannelID, 'Field', fieldID2, 'NumPoints', NumPoints, 'ReadKey', readAPIKey);

% Read third data variable
Humidity = thingSpeakRead(readChannelID, 'Field', fieldID3, 'NumPoints', NumPoints, 'ReadKey', readAPIKey);

%% Processing
%CO2
CO2 (CO2 < 400) = 400;
CO2 (CO2 > 2000) = 2000;
CQ_CO2 = (CO2 - 400)/1600;

coef = 3;
CQ_CO2 = exp(CQ_CO2*coef)/exp(coef);
%Temp
CQ_Temp=abs(Temp-23)/10;
CQ_Temp(CQ_Temp>1)=1;

%Humidity
CQ_Hum=abs(Humidity-50)/10;
CQ_Hum(CQ_Hum>1)=1;

%% Visualize Data %%

w1=1.0;
w2=0.1;
w3=0.125;

CQ = 5*(1-(CQ_CO2 * w1 + CQ_Temp*w2 + CQ_Hum * w3 )/(w1+w2+w3));
CQ = round(CQ,3);
CQ = floor(medfilt1(CQ,11)*20);

%thingSpeakPlot(time,CQ,'Grid','on','XLabel','Time','YLabel','Climate quality, %');
% Write CQ values to additional channel 
disp(CQ(length(CQ)));
thingSpeakWrite(writeChannelID,CQ(length(CQ)),'WriteKey',writeAPIKey);

