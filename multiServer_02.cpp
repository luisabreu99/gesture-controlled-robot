
/* A simple server in the internet domain using TCP.
myServer.c
D. Thiebaut
Adapted from http://www.cs.rpi.edu/~moorthy/Courses/os98/Pgms/socket.html
The port number used in 80.
This code is compiled and run on the Raspberry as follows:

    g++ -o myServer myServer.c
    ./myServer

The server waits for a connection request from a client.
The server assumes the client will send positive integers, which it sends back multiplied by 2.
If the server receives -1 it closes the socket with the client.
If the server receives -2, it exits.
*/

#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <pthread.h>
#include <assert.h>
#include <iostream>
#include <fcntl.h>
#include <termios.h>
#include "opencv2/imgproc/imgproc.hpp"
#include "opencv2/highgui/highgui.hpp"
#include "opencv2/flann/miniflann.hpp"
#include <vector>
#include <sstream>
#include <opencv2/dnn.hpp>

#define NUM_THREADS     5

typedef struct command
{
    int cmd;
    int vx;
    int vy;
    int pitch;
}st_cmd;

using namespace cv; // all the new API is put into "cv" namespace. Export its content
using namespace std;
using namespace std;
void error( char *msg );
st_cmd getData( int sockfd );
void sendData( int sockfd, char x[] );
void sendImgData( int sockfd, Mat *x );

void *task_code(void *argument);
void moveRobot(int vx,int vy,char r[]);
bool motorCmdWrite(char msg[]);
void get_motors_current(char r[]);
void get_motors_max_current(char r[]);
bool get_ack(char msg[]);
int motorReadCurrent(char r[]);
void handleWebClient(int newsockfd);
VideoCapture capture;

bool endServer=false;
int fd;


int main(int argc, char *argv[])
{
    int sockfd;
    int	newsockfd;
    int	portno = 8085;
    int clilen;
    int clientID=0;
    char buffer[256];
    struct sockaddr_in serv_addr, cli_addr;
    int n;
    pthread_t threads;//[NUM_THREADS];
    int thread_args;//[NUM_THREADS];
    int rc, i;
    
    printf("Setting serial port ttyS3 to 115200 8 bits no parity 1 stop bit \n");
    //Serial system("stty -F /dev/ttyS3 115200 cs8 cread clocal");

    //Serial desativa temporariamente
    /*
    // Open the Port. We want read/write, no "controlling tty" status, and open it no matter what state DCD is in
    fd = open("/dev/ttyS3", O_RDWR | O_NOCTTY | O_NDELAY);
    if (fd == -1)
    {
        perror("open_port: Unable to open /dev/ttyS3 - ");
        return(-1);
    }

    // Turn off blocking for reads, use (fd, F_SETFL, FNDELAY) if you want that
    fcntl(fd, F_SETFL, 0);
    */

    printf( "using port #%d\n", portno );
    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0)
        error("ERROR opening socket");
    bzero((char *) &serv_addr, sizeof(serv_addr));

    serv_addr.sin_family = AF_INET;
    serv_addr.sin_addr.s_addr = INADDR_ANY;
    serv_addr.sin_port = htons( portno );
    if (bind(sockfd, (struct sockaddr *) &serv_addr,sizeof(serv_addr)) < 0) error( "ERROR on binding" );
    listen(sockfd,5);
    clilen = sizeof(cli_addr);

    //--- infinite wait on a connection ---
    while ( 1 )
    {
        printf( "\n\n waiting for new client... %d\n",clientID );
        if ( ( newsockfd = accept( sockfd, (struct sockaddr *) &cli_addr, (socklen_t*) &clilen) ) < 0 )
            error("ERROR on accept");
        rc = pthread_create(&threads, NULL, task_code, (void *) &newsockfd);
        assert(0 == rc);
        clientID++;

        //-terminate the server ---
        if ( endServer ) break;
    }
    //Serial 	close(fd);
    close(sockfd);
    return 0;
}
void *task_code(void *argument)
{
    int newsockfd;
    st_cmd rcv;
    Mat image;
    int cmd;
    char result[30];
    newsockfd = *((int *) argument);
    printf("Start a new thread to process the client data in soket %d!\n", newsockfd);
    int key =0;
    int n;
    printf( "opened new communication with client\n" );
    // CLIENTE WEB
    char peekBuf[5];

    int peekRead = read(newsockfd, peekBuf, 4);

    if(peekRead > 0)
    {
        peekBuf[peekRead] = '\0';

        if(peekRead == 4 &&
            strncmp(peekBuf, "GET ", 4) == 0)
        {
            handleWebClient(newsockfd);
            return NULL;
        }
    }
    while ( 1 )
    {
        //---- wait for a number from client ---
        rcv  = getData( newsockfd );

        printf( "got from client %d - %d\n",newsockfd, rcv.cmd);
        if (rcv.cmd==1) break;
        if (rcv.cmd==2)
        {
            endServer=true;
            break;
        }
        if (rcv.cmd==3)
        {
            moveRobot(rcv.vx,rcv.vy,result);
            sendData( newsockfd, result );
        }
        if (rcv.cmd==4)
        {
            get_motors_current(result);
            sendData( newsockfd, result );
        }
        if (rcv.cmd==5)
        {
            get_motors_max_current(result);
            sendData( newsockfd, result );
        }
        if (rcv.cmd==10)
        {
            capture.open(0);
            if(!capture.isOpened())
            {
                cout << "Erro camera cmd10\n";
                continue;
            }
            capture >> image;
            imwrite("img.jpg",image);
            //imshow("teste",image);
            printf("\nnovo frame");
            key=waitKey(300);

            //--- send new data to client ---
            printf( "sending back o client %d% \n",newsockfd);
            sendImgData( newsockfd, &image );
            capture.release();
        }
    }
    close( newsockfd );
    /* optionally: insert more useful stuff here */
    return NULL;
}
void handleWebClient(int newsockfd)
{
    capture.open(0);

    if(!capture.isOpened())
    {
        cout << "Erro camera\n";
        close(newsockfd);
        return;
    }

    string header =
        "HTTP/1.1 200 OK\r\n"
        "Cache-Control: no-cache\r\n"
        "Connection: close\r\n"
        "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n";

    write(newsockfd, header.c_str(), header.size());

    Mat frame;

    while(true)
    {
        capture >> frame;

        if(frame.empty())
            break;
        Mat palmInput;

        resize(frame, palmInput, Size(192,192));

        Mat palmBlob = cv::dnn::blobFromImage(
            palmInput,
            1.0/255.0,
            Size(192,192),
            Scalar(),
            true,
            false
            );

        palmNet.setInput(palmBlob);

        Mat palmOutput = palmNet.forward();

        const float* data =
            (float*)palmOutput.data;

        for(int i = 0; i < 20; i++)
        {
            cout << data[i] << " ";
        }

        cout << endl;

        rectangle(frame,
                  Point(100,100),
                  Point(300,300),
                  Scalar(0,255,0),
                  3);

        vector<uchar> buffer;

        vector<int> params;

        params.push_back(IMWRITE_JPEG_QUALITY);
        params.push_back(80);

        imencode(".jpg", frame, buffer, params);

        string part =
            "--frame\r\n"
            "Content-Type: image/jpeg\r\n"
            "Content-Length: " + to_string(buffer.size()) + "\r\n\r\n";

        write(newsockfd, part.c_str(), part.size());

        if(write(newsockfd,
                  buffer.data(),
                  buffer.size()) < 0)
        {
            cout << "Cliente disconnected\n";
            break;
        }

        write(newsockfd, "\r\n", 2);

        usleep(30000);
    }

    capture.release();

    close(newsockfd);
}
void error( char *msg )
{
    printf("%s\n",msg );
    exit(1);
}
int motorReadCurrent(char r[])
{
    char buf[32];
    char cbuffer[1];

    int i=0;

    read(fd,cbuffer,1);
    while (cbuffer[0]!='<') read(fd,cbuffer,1);
    read(fd,cbuffer,1);
    while (cbuffer[0]!='>')
    {
        buf[i]=cbuffer[0];
        i++;
        if (i>31)
        {
            cout<< "To long command\n ";
            return false;
        }
        read(fd,cbuffer,1);
    }
    buf[i]=0;
    strcpy(r,buf);
    i=atoi(buf);
    //	cout<< "\nserial buffer ="<<buf<<"i="<<i<<"\n";
    return (i);
}
bool get_ack(char msg[])
{
    char buf[32];
    char cbuffer[1];

    int i=0;

    read(fd,cbuffer,1);
    while (cbuffer[0]!='<') read(fd,cbuffer,1);
    read(fd,cbuffer,1);
    buf[0]='#';
    i++;
    while (cbuffer[0]!='>')
    {
        buf[i]=cbuffer[0];
        i++;
        if (i>31)
        {
            cout<< "To long command\n ";
            return false;
        }
        read(fd,cbuffer,1);
    }
    buf[i]=0;
    i=strncmp(buf,msg,7);
    //	cout<<"\nmsg="<<msg << "\nserial buffer ="<<buf<<"i="<<i<<"\n";

    return (!i);
}

bool motorCmdWrite(char msg[])
{
    bool writeOK=true;
    int n=0;


    //usleep(10000);
    //	cout<<"msg="<<msg<<"\n";
    n += write(fd,msg,8);
    //	cout<<"Bytes sended ="<<n<<"\n";
    if (n < 0)
    {
        perror("Write failed...\n");
        writeOK=false;
    }
    //	usleep(10000);

    writeOK |= get_ack(msg);
    //	if (writeOK)	cout<<"sucesseful write command \n";
    return 	(writeOK);

}
void get_motors_max_current(char r[])
{
    char res[20];
    char M1[9],M2[9];
    M1[0]='#';
    M2[0]='#';
    M1[1]='X';
    M2[1]='X';
    M1[2]='L';
    M2[2]='R';
    M1[3]='+';
    M2[3]='+';
    M1[4]=48;
    M1[5]=48;
    M1[6]=48;
    M1[7]=13;
    M1[8]=0;

    M2[4]=48;
    M2[5]=48;
    M2[6]=48;
    M2[7]=13;
    M2[8]=0;
    //	cout<<"\nwriting to motor\n";
    //	cout<< " M1 - "<<M1<<"\n\n M2  - "<<M2<<"\n\n";
    cout<<"writing command to motor 1...\n";
    if(motorCmdWrite(M1)) cout<<"Motor 1 Command OK\n";
    cout<<"Motor 1 current = "<<motorReadCurrent(res)<<"\n";
    strcpy(r,res);
    strcat(r," , ");
    cout<<"writing command to motor 2...\n";
    if(motorCmdWrite(M2)) cout<<"Motor 2 Command ok\n";
    cout<<"Motor 2 current = "<<motorReadCurrent(res)<<"\n";
    strcat(r,res);
    strcat(r,"\n\r");

    //    cout<<"fim motor\n";

}
void get_motors_current(char r[])
{
    char res[10];
    char M1[9],M2[9];
    M1[0]='#';
    M2[0]='#';
    M1[1]='A';
    M2[1]='A';
    M1[2]='L';
    M2[2]='R';
    M1[3]='+';
    M2[3]='+';
    M1[4]=48;
    M1[5]=48;
    M1[6]=48;
    M1[7]=13;
    M1[8]=0;

    M2[4]=48;
    M2[5]=48;
    M2[6]=48;
    M2[7]=13;
    M2[8]=0;
    //	cout<<"\nwriting to motor\n";
    //	cout<< " M1 - "<<M1<<"\n\n M2  - "<<M2<<"\n\n";
    cout<<"writing command to motor 1...\n";
    if(motorCmdWrite(M1)) cout<<"Motor 1 Command OK\n";
    cout<<"Motor 1 current = "<<motorReadCurrent(res)<<"\n";
    strcpy(r,res);
    strcat(r," , ");
    cout<<"writing command to motor 2...\n";
    if(motorCmdWrite(M2)) cout<<"Motor 2 Command ok\n";
    cout<<"Motor 2 current = "<<motorReadCurrent(res)<<"\n";
    strcat(r,res);
    strcat(r,"\n\r");
    //    cout<<"fim motor\n";

}
void moveRobot(int vx, int vy,char r[])
{

    char M1[9],M2[9];
    M1[0]='#';
    M2[0]='#';
    M1[1]='M';
    M2[1]='M';
    M1[2]='L';
    M2[2]='R';
    if (vx>0) M1[3]='+'; else M1[3]='-';
    if (vy>0) M2[3]='+'; else M2[3]='-';
    M1[4]=48;
    M1[5]=48;
    M1[6]=48+((abs(vx)));
    M1[7]=13;
    M1[8]=0;

    M2[4]=48;
    M2[5]=48;
    M2[6]=48+((abs(vy)));
    M2[7]=13;
    M2[8]=0;
    //		cout<<"\nwriting to motor\n";
    //		cout<< " M1 - "<<M1<<"\n\n M2  - "<<M2<<"\n\n";
    cout<<"writing command to motor 1...\n";
    if(motorCmdWrite(M1))
    {
        cout<<"Motor 1 Command OK\n";
        strcpy(r,"M1 CMD OK\n\r");
    }
    else
    {
        cout<<"Motor 1 Command not OK\n";
        strcpy(r,"M1 CMD not OK\n\r");
    }
    cout<<"writing command to motor 2...\n";
    if(motorCmdWrite(M2))
    {
        cout<<"Motor 2 Command ok\n";
        strcat(r,"M2 CMD OK\n\r");
    }
    else
    {
        cout<<"Motor 2 Command ok\n";
        strcat(r,"M2 CMD not OK\n\r");
    }
    //    	cout<<"fim motor\n";

}
void sendImgData( int sockfd, Mat *x )
{
    int n;
    if ((n = write(sockfd, x, sizeof(x))) < 0 ) error("ERROR writing to socket");
}
void sendData( int sockfd, char x[] )
{
    int n;
    int s=strlen(x);
    if ((n = write(sockfd, x, s)) < 0 ) error("ERROR writing to socket");
}

st_cmd getData( int sockfd )
{
    st_cmd cmd;
    bool findfirst=false;
    char buffer[32];
    char aux[10];
    int n;
    int s=0;
    int i=0;
    int j=0;
    while(s<i+12)
    {
        if ( (n = read(sockfd,buffer+s,31) ) < 0 ) error( "ERROR reading from socket");
        j=i;
        s+=n;
        //			cout << buffer<<"\n";
        while(!findfirst && j<s)
        {
            if (buffer[j]=='#') findfirst=true;
            i=j;
            j++;
        }
        if (!findfirst)
        {
            s=0;
            i=0;
        }
        //			cout<<"n="<<n<<"  s="<<s<<"  i="<<i<<" j="<<j<<" find first="<<findfirst<<"\n";
    }
    i++;
    buffer[s] = '\0';
    //		cout << "\nsockect buffer ="<<buffer;
    memcpy(aux,buffer+i,2);
    aux[2]='\0';
    //		cout<<"\naux cmd ="<<aux;
    cmd.cmd=atoi(aux);

    memcpy(aux,buffer+i+2,2);
    aux[2]='\0';
    //		cout<<"\naux vx ="<<aux;
    cmd.vx=atoi(aux);

    memcpy(aux,buffer+i+4,2);
    aux[2]='\0';
    //		cout<<"\naux vy ="<<aux;
    cmd.vy=atoi(aux);

    memcpy(aux,buffer+i+6,4);
    aux[4]='\0';
    //		cout<<"\naux pitch ="<<aux;
    cmd.pitch=atoi(aux);

    //	cout << "\ncmd ="<<cmd.cmd;
    //	cout << "\nvx ="<<cmd.vx;
    //	cout << "\nvy ="<<cmd.vy;
    //	cout << "\npitch ="<<cmd.pitch;
    //	cout << "\n\n";
    return cmd;
}

